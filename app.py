from flask import Flask, request, jsonify, render_template, abort, send_file
from tempfile import NamedTemporaryFile
from whisper.utils import get_writer
import whisper
import torch
import os
import ffmpeg
import srt
import datetime


# Select device
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model("base", device=DEVICE)

# Video to audio
def is_audio(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_AUDIO

def is_video(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_VIDEO

def video_to_audio(video_path, audio_path):
    ffmpeg.input(video_path).output(audio_path).run()

ALLOWED_AUDIO = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.webm'}
ALLOWED_VIDEO = {'.mp4', '.mov', '.avi', '.webm', '.mkv'}

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "file" not in request.files:
        abort(400, description="No file uploaded")
    audio_file = request.files["file"]
    language = request.form.get("language") or None  # "" means auto

    # Save input to temp file
    with NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.filename)[1]) as tmp_input:
        audio_file.save(tmp_input.name)
        tmp_input_path = tmp_input.name

    # Convert to WAV
    with NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
        tmp_wav_path = tmp_wav.name

    try:
        ffmpeg.input(tmp_input_path).output(tmp_wav_path, format="wav", ar="16k").run(quiet=True, overwrite_output=True)

        # Transcribe
        transcribe_kwargs = {}
        if language:
            transcribe_kwargs['language'] = language
        result = model.transcribe(tmp_wav_path, **transcribe_kwargs)

        return jsonify({
            "transcript": result["text"],
            "language": result.get("language", ""),
            "segments": result.get("segments", [])
        })

    finally:
        # Clean up
        if os.path.exists(tmp_input_path):
            os.remove(tmp_input_path)
        if os.path.exists(tmp_wav_path):
            os.remove(tmp_wav_path)

@app.route("/transcribe/srt", methods=["POST"])
def transcribe_srt():
    if "file" not in request.files:
        abort(400, description="No file Uploaded")
    video_file = request.files["file"]
    language = request.form.get("language") or None

    #Temp files
    with NamedTemporaryFile(delete=False, suffix=os.path.splitext(video_file.filename)[1]) as tmp_video:
        video_file.save(tmp_video.name)
        tmp_video_path = tmp_video.name
    with NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
        tmp_audio_path = tmp_audio.name

    try:
        # Extract audio from video
        ffmpeg.input(tmp_video_path).output(tmp_audio_path, format="wav", ar="16k").run(quiet=True, overwrite_output=True)

        # Transcribe with whisper
        transcribe_kwargs = {}
        if language:
            transcribe_kwargs["language"] = language

        result = model.transcribe(tmp_audio_path, **transcribe_kwargs)

        # Build SRT subtitles
        subs = []
        for i, seg in enumerate(result.get("segments", []), start=1):
            start = datetime.timedelta(seconds=seg["start"])
            end= datetime.timedelta(seconds=seg["end"])
            subs.append(srt.Subtitle(index=i, start=start, end=end, content=seg["text"].strip()))

        srt_data = srt.compose(subs)

        # Return downloadable file
        return (
            srt_data,
            200,
            {
                "Content-Type": "application/x-subrip",
                "Content-Disposition": 'attachment; filename="subtitles.srt"'
            }
        )        

    finally:
        #Clean up temp files
        if os.path.exists(tmp_video_path):
            os.remove(tmp_video_path)
        if os.path.exists(tmp_audio_path):
            os.remove(tmp_audio_path)

#production:
#if __name__ == "__main__":
    #app.run(host="0.0.0.0", port=5000, debug=True)

# debug i development
if __name__ == "__main__":
    app.run(debug=True)
from flask import Flask, request, jsonify, render_template, abort, send_file
from tempfile import NamedTemporaryFile
from whisper.utils import get_writer
import whisper
import torch
import os
import ffmpeg


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
    with NamedTemporaryFile(delete=True, suffix=os.path.splitext(audio_file.filename)[1]) as tmp:
        audio_file.save(tmp.name)
        # Pass language if set, otherwise let Whisper auto-detect
        transcribe_kwargs = {}
        if language:
            transcribe_kwargs['language'] = language
        result = model.transcribe(tmp.name, **transcribe_kwargs)
    return jsonify({
        "transcript": result["text"],
        "language": result.get("language", ""),
        "segments": result.get("segments", [])
    })


@app.route("/transcribe/srt", methods=["POST"])
def transcribe_srt():
    if "file" not in request.files:
        abort(400, "No file uploaded")
    upload = request.files["file"]
    ext = os.path.splitext(upload.filename)[1].lower()

    with NamedTemporaryFile(delete=False, suffix=ext) as tmp_in:
        upload.save(tmp_in.name)
        audio_path = tmp_in.name

    # convert video to WAV if needed
    if is_video(upload.filename):
        with NamedTemporaryFile(delete=False, suffix='.wav') as tmp_audio:
            video_to_audio(audio_path, tmp_audio.name)
            audio_path = tmp_audio.name

    # Run Whisper transcription
    result = model.transcribe(audio_path, task="transcribe")

    # Write SRT to same dir as audio
    output_dir = os.path.dirname(audio_path)
    writer = get_writer("srt", output_dir)
    writer(result, audio_path)

    # Figure out actual generated path
    srt_path = os.path.splitext(audio_path)[0] + ".srt"
    if not os.path.exists(srt_path):
        abort(500, "SRT file was not created")

    return send_file(srt_path, as_attachment=True,
                     download_name="transcript.srt",
                     mimetype="text/plain")

#production:
#if __name__ == "__main__":
    #app.run(host="0.0.0.0", port=5000, debug=True)

# debug i development
if __name__ == "__main__":
    app.run(debug=True)
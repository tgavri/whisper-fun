from flask import Flask, request, jsonify, render_template, abort, send_file, Response
from tempfile import NamedTemporaryFile
from whisper.utils import get_writer
import whisper
import ffmpeg
import srt
import datetime
import argostranslate.package
import argostranslate.translate
import torch
import os

models_dir = os.path.join(os.path.dirname(__file__), "installed_models")
for filename in os.listdir(models_dir):
    if filename.endswith(".argosmodel"):
        model_path = os.path.join(models_dir, filename)
        argostranslate.package.install_from_path(model_path)

import argostranslate.translate
installed_languages = argostranslate.translate.get_installed_languages()
print([lang.code for lang in installed_languages])

# Commented out LLaMA loading
# model_name = "meta-llama/Llama-2-7b-hf"
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# tokenizer = LlamaTokenizer.from_pretrained(model_name)
# model = LlamaForCausalLM.from_pretrained(
#     model_name,
#     torch_dtype=torch.float16,
#     device_map="auto"
# ).to(device)

# def paraphrase_text_hf(text: str) -> str:
#     prompt = f"Paraphrase this text:\n{text}\nParaphrased:"
#     inputs = tokenizer(prompt, return_tensors="pt").to(device)
#     outputs = model.generate(
#         **inputs,
#         max_new_tokens=128,
#         temperature=0.7,
#         do_sample=True,
#         top_p=0.9
#     )
#     decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
#     _, paraphrased = decoded.split("Paraphrased:", 1)
#     return paraphrased.strip()


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model("base", device=DEVICE)

#print("CUDA Available:", torch.cuda.is_available())
#print("Current device:", torch.cuda.current_device())
#print("Device name:", torch.cuda.get_device_name(torch.cuda.current_device()))

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

@app.route("/translate", methods=["POST"])
def translate():
    if "file" not in request.files:
        abort(400, description="No file uploaded")
    audio_file = request.files["file"]
    target_language = request.form.get("language") or "en"

    # Save uploaded file to temp location (MUST do this!)
    with NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.filename)[1]) as tmp_input:
        audio_file.save(tmp_input.name)
        tmp_input_path = tmp_input.name

    # Create temp WAV file path too
    with NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
        tmp_wav_path = tmp_wav.name

    try:
        # Convert input audio to WAV with ffmpeg
        ffmpeg.input(tmp_input_path).output(tmp_wav_path, format="wav", ar="16k").run(quiet=True, overwrite_output=True)

        # Transcribe the WAV file with Whisper
        result = model.transcribe(tmp_wav_path)
        detected_language = result.get("language", "")
        original_text = result.get("text", "").strip()
        if not original_text:
            return jsonify({"error": "No speech or text detected in audio."}), 400

        # Get installed translation languages
        installed_languages = argostranslate.translate.get_installed_languages()
        from_lang = next((l for l in installed_languages if l.code == detected_language), None)
        to_lang = next((l for l in installed_languages if l.code == target_language), None)
        if not (from_lang and to_lang):
            return jsonify({"error": "Selected language(s) not installed"}), 400

        try:
            translation = from_lang.get_translation(to_lang).translate(original_text)
        except Exception as e:
            return jsonify({"error": f"Translation not possible: {str(e)}"}), 400

        return jsonify({
            "detected_language": detected_language,
            "original_text": original_text,
            "translated_text": translation
        })
    finally:
        # Clean up temp files safely
        if 'tmp_input_path' in locals() and os.path.exists(tmp_input_path):
            os.remove(tmp_input_path)
        if 'tmp_wav_path' in locals() and os.path.exists(tmp_wav_path):
            os.remove(tmp_wav_path)



#production:
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

# debug i development
#if __name__ == "__main__":
#    app.run(debug=True)

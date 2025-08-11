from flask import Flask, request, jsonify, render_template, abort
from tempfile import NamedTemporaryFile
import whisper
import torch
import os

# Select device
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model("base", device=DEVICE)

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "file" not in request.files:
        abort(400, description="No file uploaded")
    audio_file = request.files["file"]
    with NamedTemporaryFile(delete=True, suffix=os.path.splitext(audio_file.filename)[1]) as tmp:
        audio_file.save(tmp.name)
        result = model.transcribe(tmp.name)
    return jsonify({
        "transcript": result["text"],
        "language": result.get("language", ""),
        "segments": result.get("segments", [])
    })
    
#production:
#if __name__ == "__main__":
    #app.run(host="0.0.0.0", port=5000, debug=True)

# debug i development
if __name__ == "__main__":
    app.run(debug=True)
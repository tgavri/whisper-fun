from flask import Flask, request, jsonify, abort
from tempfile import NamedTemporaryFile
import whisper
import torch
import os

# Check for CUDA GPU support or use CPU fallback
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Load the Whisper model once on startup
model = whisper.load_model("base", device=DEVICE)

app = Flask(__name__)

@app.route("/")
def index():
    return "Whisper Transcription API"

@app.route("/transcribe", methods=["POST"])
def transcribe():
    # Check if file included in request
    if "file" not in request.files:
        abort(400, description="No audio file provided")
    
    audio_file = request.files["file"]

    # Save the uploaded file temporarily
    with NamedTemporaryFile(delete=True, suffix=os.path.splitext(audio_file.filename)[1]) as temp_audio:
        audio_file.save(temp_audio.name)
        # Run transcription
        result = model.transcribe(temp_audio.name)
        # Return transcript JSON
        return jsonify({
            "transcript": result["text"],
            "language": result.get("language", ""),
            "segments": result.get("segments", [])
        })

# Production entry point
#if __name__ == "__main__":
    # Use host='0.0.0.0' for external access, threaded=True for concurrency
    #app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

#debug i development
if __name__ == "__main__":
    app.run(debug=True)
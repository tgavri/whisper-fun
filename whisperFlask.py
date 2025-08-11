from flask import Flask, request, jsonify, abort, render_template_string
from tempfile import NamedTemporaryFile
import whisper
import torch
import os

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model("base", device=DEVICE)

app = Flask(__name__)

INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Whisper Transcription API</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding-top: 50px; background-color: #f8f9fa; }
        .container { max-width: 700px; }
        .result-box { white-space: pre-wrap; background: #fff; padding: 15px; border-radius: 8px; border: 1px solid #ccc; }
    </style>
</head>
<body>
<div class="container">
    <h1 class="mb-4 text-center">🎤 Whisper Audio Transcription</h1>
    <div class="card p-4 shadow-sm">
        <form id="uploadForm">
            <div class="mb-3">
                <label for="audioFile" class="form-label">Select Audio File</label>
                <input class="form-control" type="file" id="audioFile" name="file" accept=".mp3,.wav,.flac,.m4a,.ogg,.webm" required>
            </div>
            <button type="submit" class="btn btn-primary w-100">Transcribe</button>
        </form>
        <div id="loading" class="text-center mt-3" style="display:none;">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="mt-2">Transcribing… please wait</p>
        </div>
        <div id="result" class="mt-4" style="display:none;">
            <h5>Transcription Result:</h5>
            <div class="result-box" id="transcriptText"></div>
        </div>
    </div>
</div>

<script>
document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const fileInput = document.getElementById('audioFile');
    if (!fileInput.files.length) return;

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    document.getElementById('loading').style.display = 'block';
    document.getElementById('result').style.display = 'none';

    try {
        const response = await fetch('/transcribe', {
            method: 'POST',
            body: formData
        });
        if (!response.ok) throw new Error("Transcription failed");
        const data = await response.json();

        document.getElementById('loading').style.display = 'none';
        document.getElementById('result').style.display = 'block';
        document.getElementById('transcriptText').textContent = data.transcript || "[No transcript returned]";
    } catch (err) {
        document.getElementById('loading').style.display = 'none';
        alert("Error: " + err.message);
    }
});
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "file" not in request.files:
        abort(400, description="No audio file provided")
    
    audio_file = request.files["file"]

    with NamedTemporaryFile(delete=True, suffix=os.path.splitext(audio_file.filename)[1]) as temp_audio:
        audio_file.save(temp_audio.name)
        result = model.transcribe(temp_audio.name)
        return jsonify({
            "transcript": result["text"],
            "language": result.get("language", ""),
            "segments": result.get("segments", [])
        })

# Production entry point
#if __name__ == "__main__":
    # Use host='0.0.0.0' for external access, threaded=True for concurrency
    #app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

# debug i development
if __name__ == "__main__":
    app.run(debug=True)
import streamlit as st
import whisper
import tempfile
import os

# Set up the page title and layout
st.set_page_config(page_title="Whisper Audio Transcription", layout="wide")
st.title("🎤 Whisper Audio Transcription")
st.write("Upload any audio file (mp3, wav, m4a, etc.) and get instant transcription with OpenAI Whisper.")

# Load model once and cache it for performance
@st.cache_resource
def load_model():
    return whisper.load_model("base")

model = load_model()

# File uploader
audio_file = st.file_uploader(
    "Choose an audio file",
    type=["mp3", "wav", "m4a", "ogg", "flac"]
)

if audio_file is not None:
    st.audio(audio_file, format='audio/wav')
    if st.button("Transcribe"):
        # Save the uploaded file to a temp file for Whisper
        with tempfile.NamedTemporaryFile(delete=False, suffix='.' + audio_file.name.split('.')[-1]) as tmp_file:
            tmp_file.write(audio_file.read())
            tmp_filepath = tmp_file.name
        # Transcription
        with st.spinner("Transcribing..."):
            result = model.transcribe(tmp_filepath)
        os.remove(tmp_filepath)
        # Output
        st.subheader("Transcribed Text")
        st.write(result["text"])
else:
    st.info("Please upload an audio file to begin.")

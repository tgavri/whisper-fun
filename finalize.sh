<<<<<<< HEAD
=======
#!/bin/bash

RECORDINGS_DIR="$1"

if [ -z "$RECORDINGS_DIR" ]; then
    RECORDINGS_DIR="/recordings"
fi

LOG_FILE="/tmp/finalize.log"

echo "[Finalize] Running at $(date)" >> "$LOG_FILE"
echo "[Finalize] RECORDINGS_DIR=$RECORDINGS_DIR" >> "$LOG_FILE"

timestamp=$(date +%Y-%m-%d_%H-%M-%S)

# Parent directory where the session folder is located
parent_dir=$(dirname "$RECORDINGS_DIR")
# New name for the folder
new_dir="${parent_dir}/${timestamp}"

echo "[Finalize] Renaming \"$RECORDINGS_DIR\" to \"$new_dir\"" >> "$LOG_FILE"
mv "$RECORDINGS_DIR" "$new_dir"

# Find the most recent mp4 file (fixed typo: 'fin' -> 'find', spaces between options)
LATEST_FILE=$(find "$new_dir" -type f -iname "*.mp4" -printf "%T@ %p\n" | sort -n | tail -1 | cut -d' ' -f2-)

if [[ -z "$LATEST_FILE" ]]; then
    echo "[Finalize] No MP4 files found in $new_dir" >> "$LOG_FILE"
    exit 0
fi

echo "[Finalize] Latest file: $LATEST_FILE" >> "$LOG_FILE"

# Set SRT file path to match video name
BASENAME="${LATEST_FILE%.*}"
SRT_FILE="${BASENAME}.srt"

# Curl to transcription service (fixed variable name typo)
TRANSCRIPTION_URL="http://rosetta.semaphor.dk/transcribe/srt"

echo "[Finalize] Sending file to $TRANSCRIPTION_URL" >> "$LOG_FILE"
curl -s -X POST \
    "$TRANSCRIPTION_URL" \
    -F "file=@${LATEST_FILE}" \
    -o "$SRT_FILE"

if [[ -s "$SRT_FILE" ]]; then
    echo "[Finalize] SRT saved to $SRT_FILE" >> "$LOG_FILE"
else
    echo "[Finalize] Transcription failed or returned empty file" >> "$LOG_FILE"
fi

echo "[Finalize] Done." >> "$LOG_FILE"
>>>>>>> 9387861 (Fixed app so that it take more than just mp3 files, made finalize.sh so it curls and installs latest videofile into an srt file. And updated index.html so it translates the site manually via browser language)

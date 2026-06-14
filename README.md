# Subify-CLI

Subify-CLI now prints a Rich-based startup banner and extracts speech from a
video into plain transcript text using Faster-Whisper.

Install dependencies:

```bash
pip install -r requirements.txt
```

Usage:

```bash
python -m subify --help
python -m subify generate-srt video.mp4
```

`generate-srt` currently prints the transcript only. It does not create an
`.srt` file yet.

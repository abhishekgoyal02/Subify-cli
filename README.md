# Subify-CLI

A command-line tool that extracts speech from video files and generates plain-text transcripts using [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper).

Requires **FFmpeg** on your system PATH (or set `SUBIFY_FFMPEG_PATH`).

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python -m subify generate-srt video.mp4
```

The transcript is printed to stdout. SRT file output is planned for a future release.

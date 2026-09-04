# Subify-CLI

Subify-CLI is a local subtitle product for short English `.mp4` recordings. It turns spoken audio into timed text, burns that text into a new video, and delivers both artifacts in a single ZIP.

The source file is never overwritten. Current scope is `.mp4` input up to 12 minutes.

Website: [subify-cli.vercel.app](https://subify-cli.vercel.app/)

## Why it exists

A sidecar `.srt` file is useful for editing. Many players and social workflows still need **burned-in** captions: the subtitle pixels live in the picture, so the video remains readable without a separate file.

Subify keeps those two outputs together. Automatic speech recognition produces the transcript. FFmpeg hard-subtitles the frames. Packaging puts the editable SRT and the subtitled MP4 in one archive.

All of this runs on the machine that hosts Subify. Transcription uses Faster-Whisper with English locked (`language="en"`). There is no cloud transcription API in this repository.

## How the pipeline works

```text
video
  -> audio extraction
  -> English transcription
  -> SRT generation
  -> subtitle embedding
  -> ZIP packaging
```

1. **Audio extraction.** FFmpeg pulls a temporary mono 16 kHz PCM WAV, which is the format Faster-Whisper expects.
2. **Transcription.** Faster-Whisper maps that audio to timestamped English segments.
3. **SRT generation.** Those segments are written as a standard SubRip (`.srt`) file.
4. **Embedding.** FFmpeg burns the SRT into a new MP4. The original video is left untouched.
5. **Packaging.** The SRT and the subtitled MP4 are zipped for delivery.

`generate-srt` stops after step 3. `embed` starts from an existing video and SRT and only performs embedding.

## Requirements

- Python 3.11 or newer
- FFmpeg and FFprobe installed and available on `PATH`

FFmpeg is a system dependency. It is not installed by this Python package.

## Installation

Subify-CLI is not published on PyPI. Clone the repository and install in editable mode so the `subify` command is registered:

```sh
python -m pip install -e .
```

Without that install, the same entry point is:

```sh
python -m subify
```

## Usage

Running `subify` with no arguments opens the interactive shell. Slash commands drive that session:

```text
/process "lesson.mp4"
/generate-srt "lesson.mp4"
/embed "lesson.mp4" "lesson.srt"
```

Also available in the shell: `/help`, `/version`, `/config`, `/history`, `/clear`, `/doctor`, `/exit`.

The same work can be invoked directly:

| Command | What it does |
| --- | --- |
| `subify process <video>` | Full pipeline. Writes a ZIP. |
| `subify generate-srt <video>` | English `.srt` only. No embed, no ZIP. |
| `subify embed <video> <srt>` | Burns an existing SRT into a new MP4. No Whisper. |
| `subify doctor` | Checks Python, FFmpeg, FFprobe, Faster-Whisper, and write access. |

Optional flags: `--output-dir` to choose the destination, `--show-transcript` to print segments after `process` or `generate-srt`.

```sh
subify --help
subify --version
```

## Output

Default directory: `Downloads/Subify` under the current user’s home folder.

For `lesson.mp4`:

- `process` → `lesson_subify.zip` containing `lesson.srt` and `lesson_subtitled.mp4`
- `generate-srt` → `lesson.srt`
- `embed` → `lesson_subtitled.mp4`

If `lesson_subify.zip` already exists, a numbered name such as `lesson_subify (1).zip` is used.

## Telegram

The Telegram adapter polls for `.mp4` uploads, runs the same `process` pipeline, and sends the ZIP back to the chat.

Set `SUBIFY_TELEGRAM_BOT_TOKEN` in the environment, then:

```sh
python -m telegram
```

## Development

```sh
python -m venv .venv
python -m pip install -e .
python -m unittest discover -s tests
```

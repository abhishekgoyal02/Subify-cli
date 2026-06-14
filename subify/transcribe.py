"""Transcription helpers using Faster-Whisper."""

import os


def _combine_segments(segments) -> str:
    lines = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def transcribe_audio(audio_path: str, model_name: str = "base") -> str:
    """Transcribe `audio_path` and return plain text."""
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file '{audio_path}' does not exist.")

    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(model_name, device="cpu", compute_type="int8")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Faster-Whisper is not installed. Install dependencies with "
            "'pip install -r requirements.txt'."
        ) from exc
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError(
            f"Unable to load Faster-Whisper model '{model_name}': {exc}"
        ) from exc

    try:
        segments, _info = model.transcribe(audio_path)
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError(f"Faster-Whisper transcription failed: {exc}") from exc

    return _combine_segments(segments)

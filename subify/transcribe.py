"""Speech-to-text transcription."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import DependencyError, TranscriptionError

DEFAULT_LANGUAGE = "en"


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    start: float
    end: float
    text: str


def transcribe_audio(
    audio_path: Path,
    *,
    model_size: str = "small",
    language: str = DEFAULT_LANGUAGE,
) -> list[TranscriptSegment]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise DependencyError(
            "faster-whisper is not installed. Install project dependencies first."
        ) from exc

    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _info = model.transcribe(str(audio_path), language=language)
        return [
            TranscriptSegment(start=segment.start, end=segment.end, text=segment.text.strip())
            for segment in segments
            if segment.text.strip()
        ]
    except Exception as exc:
        raise TranscriptionError(f"Transcription failed: {exc}") from exc

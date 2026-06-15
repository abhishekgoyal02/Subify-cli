"""Transcription helpers using Faster-Whisper."""

import os
from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class TranscriptSegment:
    """Timestamped transcript text from a single Whisper segment."""

    start: float
    end: float
    text: str


@dataclass(frozen=True)
class TranscriptionResult:
    """Structured transcription data retained for future output formats."""

    segments: List[TranscriptSegment]

    @property
    def text(self) -> str:
        return "\n".join(segment.text for segment in self.segments if segment.text)


def _materialize_segments(segments: Iterable) -> List[TranscriptSegment]:
    return [
        TranscriptSegment(
            start=float(segment.start),
            end=float(segment.end),
            text=segment.text.strip(),
        )
        for segment in segments
    ]


def transcribe_audio_with_segments(
    audio_path: str, model_name: str = "base"
) -> TranscriptionResult:
    """Transcribe `audio_path` and return timestamped segment data."""
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
        materialized_segments = _materialize_segments(segments)
    except Exception as exc:
        raise RuntimeError(f"Faster-Whisper transcription failed: {exc}") from exc

    return TranscriptionResult(segments=materialized_segments)


def transcribe_audio(audio_path: str, model_name: str = "base") -> str:
    """Transcribe `audio_path` and return plain text."""
    return transcribe_audio_with_segments(audio_path, model_name=model_name).text

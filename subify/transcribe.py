"""Speech-to-text transcription."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from time import perf_counter

from .errors import DependencyError, TranscriptionError
from .models import TranscriptSegment

DEFAULT_LANGUAGE = "en"
DEFAULT_MODEL_SIZE = "small"
DEFAULT_DEVICE = "cpu"
DEFAULT_COMPUTE_TYPE = "int8"
DEFAULT_CPU_THREADS = None

LOGGER = logging.getLogger(__name__)


class WhisperTranscriber:
    def __init__(
        self,
        *,
        model_size: str = DEFAULT_MODEL_SIZE,
        device: str = DEFAULT_DEVICE,
        compute_type: str = DEFAULT_COMPUTE_TYPE,
        language: str = DEFAULT_LANGUAGE,
        beam_size: int | None = None,
        cpu_threads: int | None = DEFAULT_CPU_THREADS,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.beam_size = beam_size
        self.cpu_threads = cpu_threads
        self._model = None

    def transcribe_audio(self, audio_path: Path) -> list[TranscriptSegment]:
        model = self._load_model()
        options: dict[str, object] = {"language": self.language}
        if self.beam_size is not None:
            options["beam_size"] = self.beam_size

        started_at = perf_counter()
        try:
            segments, _info = model.transcribe(str(audio_path), **options)
            result = [
                TranscriptSegment(start=segment.start, end=segment.end, text=segment.text.strip())
                for segment in segments
                if segment.text.strip()
            ]
        except Exception as exc:
            raise TranscriptionError(f"Transcription failed: {exc}") from exc

        LOGGER.info(
            "Faster-Whisper transcription finished: model=%s device=%s compute_type=%s cpu_threads=%s beam_size=%s elapsed=%.2fs segments=%s",
            self.model_size,
            self.device,
            self.compute_type,
            self.cpu_threads,
            self.beam_size,
            perf_counter() - started_at,
            len(result),
        )
        return result

    def _load_model(self):
        if self._model is not None:
            return self._model

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise DependencyError(
                "faster-whisper is not installed. Install project dependencies first."
            ) from exc

        started_at = perf_counter()
        try:
            model_options: dict[str, object] = {
                "device": self.device,
                "compute_type": self.compute_type,
            }
            if self.cpu_threads is not None:
                model_options["cpu_threads"] = self.cpu_threads
            self._model = WhisperModel(self.model_size, **model_options)
        except Exception as exc:
            raise TranscriptionError(f"Transcription failed: {exc}") from exc

        LOGGER.info(
            "Faster-Whisper model loaded: model=%s device=%s compute_type=%s cpu_threads=%s elapsed=%.2fs",
            self.model_size,
            self.device,
            self.compute_type,
            self.cpu_threads,
            perf_counter() - started_at,
        )
        return self._model


def recommended_cpu_threads() -> int:
    logical_cpus = os.cpu_count()
    if logical_cpus is None:
        return 1
    return max(1, min(6, logical_cpus))


def transcribe_audio(
    audio_path: Path,
    *,
    model_size: str = DEFAULT_MODEL_SIZE,
    language: str = DEFAULT_LANGUAGE,
) -> list[TranscriptSegment]:
    return WhisperTranscriber(model_size=model_size, language=language).transcribe_audio(audio_path)

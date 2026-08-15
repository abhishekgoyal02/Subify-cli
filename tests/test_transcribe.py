import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from subify.transcribe import (
    DEFAULT_LANGUAGE,
    TranscriptSegment,
    WhisperTranscriber,
    recommended_cpu_threads,
    transcribe_audio,
)


class TranscribeTests(unittest.TestCase):
    def test_transcript_segment_preserves_timestamps_and_text(self) -> None:
        segment = TranscriptSegment(start=1.25, end=3.5, text="Hello")

        self.assertEqual(segment.start, 1.25)
        self.assertEqual(segment.end, 3.5)
        self.assertEqual(segment.text, "Hello")

    def test_transcribe_defaults_to_english_language(self) -> None:
        observed: dict[str, str] = {}

        class FakeWhisperModel:
            def __init__(self, *_args, **_kwargs) -> None:
                pass

            def transcribe(self, _audio_path: str, *, language: str):
                observed["language"] = language
                segment = types.SimpleNamespace(start=0.0, end=1.0, text=" Hello ")
                return [segment], object()

        fake_module = types.SimpleNamespace(WhisperModel=FakeWhisperModel)
        with patch.dict(sys.modules, {"faster_whisper": fake_module}):
            segments = transcribe_audio(Path("audio.wav"))

        self.assertEqual(DEFAULT_LANGUAGE, "en")
        self.assertEqual(observed["language"], "en")
        self.assertEqual(segments, [TranscriptSegment(start=0.0, end=1.0, text="Hello")])

    def test_whisper_transcriber_reuses_model_and_passes_fast_beam_size(self) -> None:
        observed: dict[str, object] = {"model_loads": 0, "calls": []}

        class FakeWhisperModel:
            def __init__(
                self,
                model_size: str,
                *,
                device: str,
                compute_type: str,
                cpu_threads: int | None = None,
            ) -> None:
                observed["model_loads"] = int(observed["model_loads"]) + 1
                observed["model_size"] = model_size
                observed["device"] = device
                observed["compute_type"] = compute_type
                observed["cpu_threads"] = cpu_threads

            def transcribe(self, audio_path: str, **options):
                observed["calls"].append((audio_path, options))
                segment = types.SimpleNamespace(start=0.0, end=1.0, text=" cached ")
                return [segment], object()

        fake_module = types.SimpleNamespace(WhisperModel=FakeWhisperModel)
        transcriber = WhisperTranscriber(beam_size=1, cpu_threads=6)

        with patch.dict(sys.modules, {"faster_whisper": fake_module}):
            first = transcriber.transcribe_audio(Path("first.wav"))
            second = transcriber.transcribe_audio(Path("second.wav"))

        self.assertEqual(observed["model_loads"], 1)
        self.assertEqual(observed["model_size"], "small")
        self.assertEqual(observed["device"], "cpu")
        self.assertEqual(observed["compute_type"], "int8")
        self.assertEqual(observed["cpu_threads"], 6)
        self.assertEqual(
            observed["calls"],
            [
                ("first.wav", {"language": "en", "beam_size": 1}),
                ("second.wav", {"language": "en", "beam_size": 1}),
            ],
        )
        self.assertEqual(first, [TranscriptSegment(start=0.0, end=1.0, text="cached")])
        self.assertEqual(second, [TranscriptSegment(start=0.0, end=1.0, text="cached")])

    @patch("subify.transcribe.os.cpu_count", return_value=12)
    def test_recommended_cpu_threads_uses_physical_core_style_heuristic(self, _cpu_count) -> None:
        self.assertEqual(recommended_cpu_threads(), 6)


if __name__ == "__main__":
    unittest.main()

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from subify.transcribe import DEFAULT_LANGUAGE, TranscriptSegment, transcribe_audio


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


if __name__ == "__main__":
    unittest.main()

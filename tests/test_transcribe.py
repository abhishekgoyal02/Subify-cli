import os
import sys
import tempfile
import types
import unittest
from types import SimpleNamespace
from unittest import mock

from subify import transcribe


class TranscribeTests(unittest.TestCase):
    def setUp(self):
        self.audio_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self.audio_file.close()

    def tearDown(self):
        if os.path.exists(self.audio_file.name):
            os.remove(self.audio_file.name)

    def _faster_whisper_module(self, segments):
        module = types.ModuleType("faster_whisper")

        class FakeWhisperModel:
            def __init__(self, model_name, device, compute_type):
                self.model_name = model_name
                self.device = device
                self.compute_type = compute_type

            def transcribe(self, audio_path):
                return segments, SimpleNamespace()

        module.WhisperModel = FakeWhisperModel
        return module

    def test_structured_result_preserves_timestamps_and_plain_text(self):
        segments = iter(
            [
                SimpleNamespace(start=0.25, end=1.5, text=" Hello "),
                SimpleNamespace(start=1.5, end=2.0, text=" "),
                SimpleNamespace(start=2.0, end=3.25, text="world"),
            ]
        )

        with mock.patch.dict(
            sys.modules,
            {"faster_whisper": self._faster_whisper_module(segments)},
        ):
            result = transcribe.transcribe_audio_with_segments(self.audio_file.name)

        self.assertEqual(result.text, "Hello\nworld")
        self.assertEqual(
            result.segments,
            [
                transcribe.TranscriptSegment(0.25, 1.5, "Hello"),
                transcribe.TranscriptSegment(1.5, 2.0, ""),
                transcribe.TranscriptSegment(2.0, 3.25, "world"),
            ],
        )

    def test_plain_text_api_remains_backward_compatible(self):
        segments = iter(
            [SimpleNamespace(start=0.0, end=1.0, text=" Existing output ")]
        )

        with mock.patch.dict(
            sys.modules,
            {"faster_whisper": self._faster_whisper_module(segments)},
        ):
            transcript = transcribe.transcribe_audio(self.audio_file.name)

        self.assertEqual(transcript, "Existing output")

    def test_lazy_segment_failure_is_wrapped(self):
        def failing_segments():
            raise ValueError("decoder failed")
            yield

        with mock.patch.dict(
            sys.modules,
            {"faster_whisper": self._faster_whisper_module(failing_segments())},
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Faster-Whisper transcription failed: decoder failed",
            ):
                transcribe.transcribe_audio(self.audio_file.name)


if __name__ == "__main__":
    unittest.main()

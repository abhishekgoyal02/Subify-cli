import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from subify import cli


class GenerateSrtTests(unittest.TestCase):
    def setUp(self):
        self.input_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        self.input_file.close()
        pipeline_patcher = mock.patch("subify.cli.update_pipeline")
        self.update_pipeline = pipeline_patcher.start()
        self.addCleanup(pipeline_patcher.stop)

    def tearDown(self):
        if os.path.exists(self.input_file.name):
            os.remove(self.input_file.name)

    @mock.patch("subify.cli.transcribe.transcribe_audio_with_segments")
    @mock.patch("subify.cli.ffmpeg_utils.extract_audio")
    def test_temporary_audio_is_removed_after_success(
        self, extract_audio, transcribe_audio_with_segments
    ):
        from subify.transcribe import TranscriptionResult, TranscriptSegment
        mock_result = TranscriptionResult(
            segments=[TranscriptSegment(start=0.0, end=2.0, text="Hello")]
        )
        transcribe_audio_with_segments.return_value = mock_result

        srt_path = os.path.splitext(self.input_file.name)[0] + ".srt"
        self.addCleanup(lambda: os.path.exists(srt_path) and os.remove(srt_path))

        cli._generate_srt(SimpleNamespace(input=self.input_file.name))

        audio_path = extract_audio.call_args.kwargs["audio_out"]
        self.assertNotEqual(audio_path, "audio.wav")
        self.assertFalse(os.path.exists(audio_path))
        self.assertEqual(
            self.update_pipeline.call_args_list,
            [mock.call(stage=1), mock.call(stage=2), mock.call(stage=3)],
        )
        self.assertTrue(os.path.exists(srt_path))
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Hello", content)

    @mock.patch(
        "subify.cli.ffmpeg_utils.extract_audio",
        side_effect=RuntimeError("extraction failed"),
    )
    def test_temporary_audio_is_removed_after_failure(self, extract_audio):
        with self.assertRaises(SystemExit) as exit_context:
            cli._generate_srt(SimpleNamespace(input=self.input_file.name))

        audio_path = extract_audio.call_args.kwargs["audio_out"]
        self.assertEqual(exit_context.exception.code, 1)
        self.assertFalse(os.path.exists(audio_path))
        self.update_pipeline.assert_called_once_with(stage=1)

    @mock.patch(
        "subify.cli.transcribe.transcribe_audio_with_segments",
        side_effect=RuntimeError("transcription failed"),
    )
    @mock.patch("subify.cli.ffmpeg_utils.extract_audio")
    def test_temporary_audio_is_removed_after_transcription_failure(
        self, extract_audio, _transcribe_audio
    ):
        with self.assertRaises(SystemExit) as exit_context:
            cli._generate_srt(SimpleNamespace(input=self.input_file.name))

        audio_path = extract_audio.call_args.kwargs["audio_out"]
        self.assertEqual(exit_context.exception.code, 1)
        self.assertFalse(os.path.exists(audio_path))
        self.assertEqual(
            self.update_pipeline.call_args_list,
            [mock.call(stage=1), mock.call(stage=2)],
        )

    @mock.patch("subify.cli.transcribe.transcribe_audio_with_segments")
    @mock.patch("subify.cli.ffmpeg_utils.extract_audio")
    def test_empty_transcription_result_aborts(
        self, extract_audio, transcribe_audio_with_segments
    ):
        from subify.transcribe import TranscriptionResult
        mock_result = TranscriptionResult(segments=[])
        transcribe_audio_with_segments.return_value = mock_result

        with self.assertRaises(SystemExit) as exit_context:
            cli._generate_srt(SimpleNamespace(input=self.input_file.name))

        self.assertEqual(exit_context.exception.code, 1)
        srt_path = os.path.splitext(self.input_file.name)[0] + ".srt"
        self.assertFalse(os.path.exists(srt_path))

    @mock.patch("subify.cli.transcribe.transcribe_audio_with_segments")
    @mock.patch("subify.cli.ffmpeg_utils.extract_audio")
    @mock.patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_write_permission_denied_handled(
        self, _mock_open, extract_audio, transcribe_audio_with_segments
    ):
        from subify.transcribe import TranscriptionResult, TranscriptSegment
        mock_result = TranscriptionResult(
            segments=[TranscriptSegment(start=0.0, end=2.0, text="Hello")]
        )
        transcribe_audio_with_segments.return_value = mock_result

        with self.assertRaises(SystemExit) as exit_context:
            cli._generate_srt(SimpleNamespace(input=self.input_file.name))

        self.assertEqual(exit_context.exception.code, 1)

    @mock.patch("subify.cli.ffmpeg_utils.extract_audio")
    def test_directory_input_is_rejected_before_extraction(self, extract_audio):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SystemExit) as exit_context:
                cli._generate_srt(SimpleNamespace(input=directory))

        self.assertEqual(exit_context.exception.code, 1)
        extract_audio.assert_not_called()
        self.update_pipeline.assert_not_called()

    @mock.patch("subify.cli.os.access", return_value=False)
    @mock.patch("subify.cli.ffmpeg_utils.extract_audio")
    def test_unreadable_input_is_rejected_before_extraction(
        self, extract_audio, _access
    ):
        with self.assertRaises(SystemExit) as exit_context:
            cli._generate_srt(SimpleNamespace(input=self.input_file.name))

        self.assertEqual(exit_context.exception.code, 1)
        extract_audio.assert_not_called()
        self.update_pipeline.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from subify.cli import main
from subify.errors import InputValidationError
from subify.models import TranscriptSegment
from subify.pipeline import EmbedResult, GenerateSRTResult, ProcessResult


class CLITests(unittest.TestCase):
    @patch("subify.cli.render_welcome")
    def test_no_command_renders_welcome_screen(self, render_welcome) -> None:
        exit_code = main([])

        self.assertEqual(exit_code, 0)
        render_welcome.assert_called_once()

    @patch("subify.ui.console", None)
    def test_plain_welcome_contains_subify_and_version(self) -> None:
        from subify import __version__
        from subify.ui import render_welcome

        stdout = StringIO()
        with patch("sys.stdout", stdout):
            render_welcome(__version__, Path("project"))

        output = stdout.getvalue()
        self.assertIn("Subify", output)
        self.assertIn(__version__, output)

    def test_version_returns_success(self) -> None:
        with self.assertRaises(SystemExit) as context:
            main(["--version"])
        self.assertEqual(context.exception.code, 0)

    @patch("subify.cli.render_welcome")
    def test_version_does_not_render_welcome(self, render_welcome) -> None:
        with self.assertRaises(SystemExit):
            main(["--version"])

        render_welcome.assert_not_called()

    @patch("subify.cli.process_video")
    def test_process_calls_pipeline(self, process_video) -> None:
        process_video.return_value = ProcessResult(zip_path=Path("output/video_subify.zip"), segments=[])

        exit_code = main(["process", "video.mp4"])

        self.assertEqual(exit_code, 0)
        call = process_video.call_args
        self.assertEqual(call.args[0], Path("video.mp4"))
        self.assertEqual(call.kwargs["output_dir"], Path("output"))

    @patch("subify.cli.process_video")
    def test_process_maps_pipeline_error_to_nonzero_exit(self, process_video) -> None:
        process_video.side_effect = InputValidationError("missing input")

        exit_code = main(["process", "missing.mp4"])

        self.assertEqual(exit_code, 1)

    @patch("subify.cli.generate_srt")
    def test_generate_srt_calls_pipeline_with_path_containing_spaces(self, generate_srt) -> None:
        generate_srt.return_value = GenerateSRTResult(
            srt_path=Path("output/my lesson.srt"),
            segments=[],
        )

        exit_code = main(["generate-srt", "my lesson.mp4"])

        self.assertEqual(exit_code, 0)
        call = generate_srt.call_args
        self.assertEqual(call.args[0], Path("my lesson.mp4"))
        self.assertEqual(call.kwargs["output_dir"], Path("output"))

    @patch("subify.cli.embed_existing_subtitles")
    def test_embed_calls_pipeline_without_transcription(self, embed_existing_subtitles) -> None:
        embed_existing_subtitles.return_value = EmbedResult(
            video_path=Path("output/lesson_subtitled.mp4")
        )

        exit_code = main(["embed", "lesson.mp4", "lesson.srt"])

        self.assertEqual(exit_code, 0)
        call = embed_existing_subtitles.call_args
        self.assertEqual(call.args[:2], (Path("lesson.mp4"), Path("lesson.srt")))

    @patch("subify.cli._print_dependency_status")
    @patch("subify.cli.process_video")
    @patch("subify.cli.render_welcome")
    def test_welcome_not_rendered_for_process(
        self,
        render_welcome,
        process_video,
        _print_dependency_status,
    ) -> None:
        process_video.return_value = ProcessResult(zip_path=Path("output/video_subify.zip"), segments=[])

        exit_code = main(["process", "video.mp4"])

        self.assertEqual(exit_code, 0)
        render_welcome.assert_not_called()

    @patch("subify.cli._print_dependency_status")
    @patch("subify.cli.process_video")
    def test_process_progress_stages_are_command_specific(
        self,
        process_video,
        _print_dependency_status,
    ) -> None:
        observed: list[tuple[str, str]] = []

        def run_pipeline(_video_path: Path, *, output_dir: Path, progress_callback):
            for stage in [
                "audio_extraction",
                "english_transcription",
                "srt_generation",
                "subtitle_embedding",
                "zip_packaging",
            ]:
                progress_callback(stage, "start")
                progress_callback(stage, "complete")
            return ProcessResult(zip_path=Path("output/video_subify.zip"), segments=[])

        process_video.side_effect = run_pipeline
        with patch("subify.ui.print_message") as print_message:
            exit_code = main(["process", "video.mp4"])

        self.assertEqual(exit_code, 0)
        observed = [call.args[0] for call in print_message.call_args_list]
        self.assertTrue(any("Audio extraction" in message for message in observed))
        self.assertTrue(any("Subtitle embedding" in message for message in observed))
        self.assertTrue(any("ZIP packaging" in message for message in observed))

    @patch("subify.cli._print_dependency_status")
    @patch("subify.cli.generate_srt")
    def test_generate_srt_does_not_show_embedding_stage(
        self,
        generate_srt,
        _print_dependency_status,
    ) -> None:
        def run_pipeline(_video_path: Path, *, output_dir: Path, progress_callback):
            for stage in ["audio_extraction", "english_transcription", "srt_generation"]:
                progress_callback(stage, "start")
                progress_callback(stage, "complete")
            return GenerateSRTResult(srt_path=Path("output/video.srt"), segments=[])

        generate_srt.side_effect = run_pipeline
        with patch("subify.ui.print_message") as print_message:
            exit_code = main(["generate-srt", "video.mp4"])

        self.assertEqual(exit_code, 0)
        messages = "\n".join(call.args[0] for call in print_message.call_args_list)
        self.assertIn("SRT generation", messages)
        self.assertNotIn("Subtitle embedding", messages)

    @patch("subify.cli._print_dependency_status")
    @patch("subify.cli.process_video")
    def test_transcript_hidden_by_default(
        self,
        process_video,
        _print_dependency_status,
    ) -> None:
        process_video.return_value = ProcessResult(
            zip_path=Path("output/video_subify.zip"),
            segments=[TranscriptSegment(0.0, 1.0, "Hidden transcript")],
        )

        with patch("subify.ui.print_message") as print_message:
            exit_code = main(["process", "video.mp4"])

        self.assertEqual(exit_code, 0)
        messages = "\n".join(call.args[0] for call in print_message.call_args_list)
        self.assertNotIn("Hidden transcript", messages)

    @patch("subify.cli._print_dependency_status")
    @patch("subify.cli.process_video")
    def test_show_transcript_prints_segments(
        self,
        process_video,
        _print_dependency_status,
    ) -> None:
        process_video.return_value = ProcessResult(
            zip_path=Path("output/video_subify.zip"),
            segments=[TranscriptSegment(0.0, 1.0, "Shown transcript")],
        )

        with patch("subify.ui.print_message") as print_message:
            exit_code = main(["process", "video.mp4", "--show-transcript"])

        self.assertEqual(exit_code, 0)
        messages = "\n".join(call.args[0] for call in print_message.call_args_list)
        self.assertIn("Shown transcript", messages)

    def test_help_lists_public_commands(self) -> None:
        stdout = StringIO()
        with patch("sys.stdout", stdout), self.assertRaises(SystemExit) as context:
            main(["--help"])

        self.assertEqual(context.exception.code, 0)
        help_output = stdout.getvalue()
        self.assertIn("process", help_output)
        self.assertIn("generate-srt", help_output)
        self.assertIn("embed", help_output)

    @patch("subify.cli.render_welcome")
    def test_help_does_not_render_welcome(self, render_welcome) -> None:
        with patch("sys.stdout", StringIO()), self.assertRaises(SystemExit):
            main(["--help"])

        render_welcome.assert_not_called()

    @patch("subify.ui.console", None)
    @patch("subify.cli.find_ffmpeg")
    @patch("subify.cli.importlib.util.find_spec")
    def test_dependency_status_reflects_runtime_detection(self, find_spec, find_ffmpeg) -> None:
        from subify.cli import _print_dependency_status

        find_ffmpeg.return_value = "ffmpeg"
        find_spec.return_value = object()
        stdout = StringIO()

        with patch("sys.stdout", stdout):
            _print_dependency_status(include_whisper=True)

        output = stdout.getvalue()
        self.assertIn("FFmpeg         Ready", output)
        self.assertIn("Faster-Whisper Ready", output)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from subify.errors import DependencyError, EmbeddingError, InputValidationError, PackagingError
from subify.pipeline import (
    MAX_SUPPORTED_VIDEO_DURATION_SECONDS,
    dependency_status,
    embed_existing_subtitles,
    generate_srt,
    process_video,
    validate_output_and_temporary_space,
    validate_input_video,
    validate_runtime_dependencies,
    validate_supported_duration,
)


class PipelineTests(unittest.TestCase):
    def test_validate_input_rejects_missing_file(self) -> None:
        with self.assertRaises(InputValidationError):
            validate_input_video(Path("does-not-exist.mp4"))

    def test_validate_input_rejects_non_mp4_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            source = Path(temp_dir_name) / "lesson.mkv"
            source.write_bytes(b"video")

            with self.assertRaises(InputValidationError) as context:
                validate_input_video(source)

        self.assertIn(".mp4", str(context.exception))

    def test_process_reports_input_validation_before_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            source = temp_dir / "lesson.mp4"
            source.write_bytes(b"video")
            output_dir = temp_dir / "output"
            observed: list[tuple[str, str]] = []

            with (
                patch("subify.pipeline.validate_runtime_dependencies"),
                patch("subify.pipeline.probe_video_duration", return_value=12.0),
                patch("subify.pipeline.extract_audio") as extract_audio,
                patch("subify.pipeline.transcribe_audio", return_value=[]),
                patch("subify.pipeline.write_srt"),
                patch("subify.pipeline.embed_subtitles"),
                patch("subify.pipeline.create_result_zip", return_value=output_dir / "lesson_subify.zip"),
            ):
                process_video(source, output_dir=output_dir, progress_callback=observed.append)

        self.assertEqual(observed[0], ("input_validation", "start"))
        self.assertEqual(observed[1], ("input_validation", "complete"))
        self.assertEqual(observed[2], ("dependency_validation", "start"))
        self.assertEqual(observed[4], ("duration_validation", "start"))
        self.assertEqual(observed[6], ("disk_space_validation", "start"))
        extract_audio.assert_called_once()

    def test_validation_failure_reports_start_without_complete(self) -> None:
        observed: list[tuple[str, str]] = []

        with self.assertRaises(InputValidationError):
            process_video("does-not-exist.mp4", progress_callback=observed.append)

        self.assertEqual(observed, [("input_validation", "start")])

    @patch("subify.pipeline.create_result_zip")
    @patch("subify.pipeline.embed_subtitles")
    @patch("subify.pipeline.write_srt")
    @patch("subify.pipeline.transcribe_audio")
    @patch("subify.pipeline.extract_audio")
    @patch("subify.pipeline.probe_video_duration", return_value=12.0)
    @patch("subify.pipeline.validate_runtime_dependencies")
    def test_process_uses_temporary_directory_and_cleans_it(
        self,
        _validate_runtime_dependencies,
        _probe_video_duration,
        extract_audio,
        transcribe_audio,
        write_srt,
        embed_subtitles,
        create_result_zip,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            source = temp_dir / "lesson.mp4"
            source.write_bytes(b"video")
            output_dir = temp_dir / "output"
            observed_temp_paths: list[Path] = []

            def record_audio(_source: Path, audio_path: Path) -> None:
                observed_temp_paths.append(audio_path.parent)
                audio_path.write_bytes(b"audio")

            extract_audio.side_effect = record_audio
            transcribe_audio.return_value = []
            create_result_zip.return_value = output_dir / "lesson_subify.zip"

            result = process_video(source, output_dir=output_dir)

            self.assertEqual(result.zip_path, output_dir / "lesson_subify.zip")
            self.assertEqual(result.language, "en")
            self.assertGreaterEqual(result.elapsed_time, 0.0)
            self.assertEqual(len(observed_temp_paths), 1)
            self.assertFalse(observed_temp_paths[0].exists())

    @patch("subify.pipeline.write_srt")
    @patch("subify.pipeline.transcribe_audio")
    @patch("subify.pipeline.extract_audio")
    @patch("subify.pipeline.probe_video_duration", return_value=12.0)
    @patch("subify.pipeline.validate_runtime_dependencies")
    def test_generate_srt_outputs_srt_and_cleans_temporary_audio(
        self,
        _validate_runtime_dependencies,
        _probe_video_duration,
        extract_audio,
        transcribe_audio,
        write_srt,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            source = temp_dir / "lesson with spaces.mp4"
            source.write_bytes(b"video")
            output_dir = temp_dir / "output"
            observed_temp_paths: list[Path] = []

            def record_audio(_source: Path, audio_path: Path) -> None:
                observed_temp_paths.append(audio_path.parent)
                audio_path.write_bytes(b"audio")

            def create_srt(_segments, srt_path: Path) -> None:
                srt_path.write_text("subtitle", encoding="utf-8")

            extract_audio.side_effect = record_audio
            transcribe_audio.return_value = []
            write_srt.side_effect = create_srt

            result = generate_srt(source, output_dir=output_dir)

            self.assertEqual(result.srt_path, output_dir / "lesson with spaces.srt")
            self.assertEqual(result.language, "en")
            self.assertGreaterEqual(result.elapsed_time, 0.0)
            self.assertTrue(result.srt_path.exists())
            self.assertFalse(observed_temp_paths[0].exists())

    @patch("subify.pipeline.embed_subtitles")
    @patch("subify.pipeline.probe_video_duration", return_value=12.0)
    @patch("subify.pipeline.validate_runtime_dependencies")
    def test_embed_existing_subtitles_outputs_subtitled_video(
        self,
        _validate_runtime_dependencies,
        _probe_video_duration,
        embed_subtitles,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            source = temp_dir / "lesson.mp4"
            srt = temp_dir / "lesson.srt"
            output_dir = temp_dir / "output"
            source.write_bytes(b"video")
            srt.write_text("subtitle", encoding="utf-8")

            def create_video(_source: Path, _srt: Path, output_path: Path) -> None:
                output_path.write_bytes(b"subtitled")

            embed_subtitles.side_effect = create_video

            result = embed_existing_subtitles(source, srt, output_dir=output_dir)

            self.assertEqual(result.video_path, output_dir / "lesson_subtitled.mp4")
            self.assertEqual(result.language, "en")
            self.assertGreaterEqual(result.elapsed_time, 0.0)
            self.assertTrue(result.video_path.exists())

    @patch("subify.pipeline.embed_subtitles")
    @patch("subify.pipeline.probe_video_duration", return_value=12.0)
    @patch("subify.pipeline.validate_runtime_dependencies")
    def test_embed_temporary_workspace_is_not_inside_output_directory(
        self,
        _validate_runtime_dependencies,
        _probe_video_duration,
        embed_subtitles,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            source = temp_dir / "lesson.mp4"
            srt = temp_dir / "lesson.srt"
            output_dir = temp_dir / "output"
            source.write_bytes(b"video")
            srt.write_text("subtitle", encoding="utf-8")
            observed_output_path: list[Path] = []

            def create_video(_source: Path, _srt: Path, output_path: Path) -> None:
                observed_output_path.append(output_path)
                output_path.write_bytes(b"subtitled")

            embed_subtitles.side_effect = create_video

            embed_existing_subtitles(source, srt, output_dir=output_dir)

            self.assertEqual(len(observed_output_path), 1)
            self.assertFalse(observed_output_path[0].is_relative_to(output_dir))
            self.assertFalse(observed_output_path[0].parent.exists())

    @patch("subify.pipeline.probe_video_duration", return_value=MAX_SUPPORTED_VIDEO_DURATION_SECONDS + 1)
    def test_duration_limit_rejects_videos_over_12_minutes(self, _probe_video_duration) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            source = Path(temp_dir_name) / "long lesson.mp4"
            source.write_bytes(b"video")

            with self.assertRaises(InputValidationError) as context:
                validate_supported_duration(source)

        self.assertIn("12 minutes", str(context.exception))

    @patch("subify.pipeline.TemporaryDirectory")
    @patch("subify.pipeline.probe_video_duration", return_value=MAX_SUPPORTED_VIDEO_DURATION_SECONDS + 1)
    @patch("subify.pipeline.validate_runtime_dependencies")
    def test_long_video_rejection_does_not_create_temporary_workspace(
        self,
        _validate_runtime_dependencies,
        _probe_video_duration,
        temporary_directory,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            source = Path(temp_dir_name) / "long lesson.mp4"
            source.write_bytes(b"video")

            with self.assertRaises(InputValidationError):
                process_video(source, output_dir=Path(temp_dir_name) / "output")

        temporary_directory.assert_not_called()

    @patch("subify.pipeline.shutil.disk_usage")
    def test_disk_space_validation_rejects_low_space(self, disk_usage) -> None:
        disk_usage.return_value = SimpleNamespace(free=5)
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            source = temp_dir / "lesson.mp4"
            source.write_bytes(b"video")

            with self.assertRaises(InputValidationError) as context:
                validate_output_and_temporary_space(source, temp_dir / "output")

        self.assertIn("Not enough", str(context.exception))

    def test_output_directory_validation_rejects_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            source = temp_dir / "lesson.mp4"
            output_file = temp_dir / "output-file"
            source.write_bytes(b"video")
            output_file.write_text("not a directory", encoding="utf-8")

            with self.assertRaises(InputValidationError) as context:
                validate_output_and_temporary_space(source, output_file)

        self.assertIn("not a directory", str(context.exception))

    @patch("subify.pipeline.find_ffprobe")
    @patch("subify.pipeline.find_ffmpeg")
    @patch("subify.pipeline.importlib.util.find_spec")
    def test_dependency_validation_requires_runtime_tools_and_python_packages(
        self,
        find_spec,
        find_ffmpeg,
        find_ffprobe,
    ) -> None:
        find_ffmpeg.return_value = "ffmpeg"
        find_ffprobe.return_value = "ffprobe"
        find_spec.return_value = object()

        validate_runtime_dependencies(require_whisper=True)

        find_ffmpeg.assert_called_once()
        find_ffprobe.assert_called_once()
        self.assertEqual(find_spec.call_count, 2)

    @patch("subify.pipeline.find_ffprobe")
    @patch("subify.pipeline.find_ffmpeg")
    @patch("subify.pipeline.importlib.util.find_spec", side_effect=[object(), None])
    def test_dependency_validation_rejects_missing_whisper(
        self,
        _find_spec,
        _find_ffmpeg,
        _find_ffprobe,
    ) -> None:
        with self.assertRaises(DependencyError) as context:
            validate_runtime_dependencies(require_whisper=True)

        self.assertIn("faster-whisper", str(context.exception))

    @patch("subify.pipeline.find_ffprobe")
    @patch("subify.pipeline.find_ffmpeg")
    def test_dependency_status_checks_ffmpeg_and_ffprobe(self, find_ffmpeg, find_ffprobe) -> None:
        find_ffmpeg.return_value = "ffmpeg"
        find_ffprobe.return_value = "ffprobe"

        ffmpeg_ready, whisper_ready = dependency_status(include_whisper=False)

        self.assertTrue(ffmpeg_ready)
        self.assertTrue(whisper_ready)
        find_ffmpeg.assert_called_once()
        find_ffprobe.assert_called_once()

    @patch("subify.pipeline.create_result_zip")
    @patch("subify.pipeline.embed_subtitles", side_effect=EmbeddingError("embed failed"))
    @patch("subify.pipeline.write_srt")
    @patch("subify.pipeline.transcribe_audio", return_value=[])
    @patch("subify.pipeline.extract_audio")
    @patch("subify.pipeline.probe_video_duration", return_value=12.0)
    @patch("subify.pipeline.validate_runtime_dependencies")
    def test_process_stops_cleanly_when_embedding_fails(
        self,
        _validate_runtime_dependencies,
        _probe_video_duration,
        _extract_audio,
        _transcribe_audio,
        _write_srt,
        _embed_subtitles,
        create_result_zip,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            source = Path(temp_dir_name) / "lesson.mp4"
            source.write_bytes(b"video")

            with self.assertRaises(EmbeddingError):
                process_video(source, output_dir=Path(temp_dir_name) / "output")

        create_result_zip.assert_not_called()

    @patch("subify.pipeline.embed_subtitles", side_effect=EmbeddingError("embed failed"))
    @patch("subify.pipeline.write_srt")
    @patch("subify.pipeline.transcribe_audio", return_value=[])
    @patch("subify.pipeline.extract_audio")
    @patch("subify.pipeline.probe_video_duration", return_value=12.0)
    @patch("subify.pipeline.validate_runtime_dependencies")
    def test_process_cleans_temporary_workspace_when_embedding_fails(
        self,
        _validate_runtime_dependencies,
        _probe_video_duration,
        extract_audio,
        _transcribe_audio,
        _write_srt,
        _embed_subtitles,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            source = Path(temp_dir_name) / "lesson.mp4"
            source.write_bytes(b"video")
            observed_temp_paths: list[Path] = []

            def record_audio(_source: Path, audio_path: Path) -> None:
                observed_temp_paths.append(audio_path.parent)

            extract_audio.side_effect = record_audio

            with self.assertRaises(EmbeddingError):
                process_video(source, output_dir=Path(temp_dir_name) / "output")

            self.assertEqual(len(observed_temp_paths), 1)
            self.assertFalse(observed_temp_paths[0].exists())

    @patch("subify.pipeline.create_result_zip", side_effect=PackagingError("zip failed"))
    @patch("subify.pipeline.embed_subtitles")
    @patch("subify.pipeline.write_srt")
    @patch("subify.pipeline.transcribe_audio", return_value=[])
    @patch("subify.pipeline.extract_audio")
    @patch("subify.pipeline.probe_video_duration", return_value=12.0)
    @patch("subify.pipeline.validate_runtime_dependencies")
    def test_process_cleans_temporary_workspace_when_packaging_fails(
        self,
        _validate_runtime_dependencies,
        _probe_video_duration,
        extract_audio,
        _transcribe_audio,
        _write_srt,
        _embed_subtitles,
        _create_result_zip,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            source = Path(temp_dir_name) / "lesson.mp4"
            source.write_bytes(b"video")
            observed_temp_paths: list[Path] = []

            def record_audio(_source: Path, audio_path: Path) -> None:
                observed_temp_paths.append(audio_path.parent)

            extract_audio.side_effect = record_audio

            with self.assertRaises(PackagingError):
                process_video(source, output_dir=Path(temp_dir_name) / "output")

            self.assertEqual(len(observed_temp_paths), 1)
            self.assertFalse(observed_temp_paths[0].exists())


if __name__ == "__main__":
    unittest.main()

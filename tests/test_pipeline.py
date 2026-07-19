import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from subify.errors import InputValidationError
from subify.pipeline import embed_existing_subtitles, generate_srt, process_video, validate_input_video


class PipelineTests(unittest.TestCase):
    def test_validate_input_rejects_missing_file(self) -> None:
        with self.assertRaises(InputValidationError):
            validate_input_video(Path("does-not-exist.mp4"))

    @patch("subify.pipeline.create_result_zip")
    @patch("subify.pipeline.embed_subtitles")
    @patch("subify.pipeline.write_srt")
    @patch("subify.pipeline.transcribe_audio")
    @patch("subify.pipeline.extract_audio")
    def test_process_uses_temporary_directory_and_cleans_it(
        self,
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
            self.assertEqual(len(observed_temp_paths), 1)
            self.assertFalse(observed_temp_paths[0].exists())

    @patch("subify.pipeline.write_srt")
    @patch("subify.pipeline.transcribe_audio")
    @patch("subify.pipeline.extract_audio")
    def test_generate_srt_outputs_srt_and_cleans_temporary_audio(
        self,
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
            self.assertTrue(result.srt_path.exists())
            self.assertFalse(observed_temp_paths[0].exists())

    @patch("subify.pipeline.embed_subtitles")
    def test_embed_existing_subtitles_outputs_subtitled_video(self, embed_subtitles) -> None:
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
            self.assertTrue(result.video_path.exists())


if __name__ == "__main__":
    unittest.main()

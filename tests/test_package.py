import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from subify.errors import PackagingError
from subify.package import create_result_zip


class PackageTests(unittest.TestCase):
    def test_zip_contains_only_expected_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            srt_path = temp_dir / "generated.srt"
            video_path = temp_dir / "lesson_subtitled.mp4"
            output_dir = temp_dir / "output"
            output_dir.mkdir()
            zip_path = output_dir / "lesson_subify.zip"
            srt_path.write_text("subtitle", encoding="utf-8")
            video_path.write_bytes(b"video")

            result = create_result_zip(
                original_video=Path("lesson.mp4"),
                srt_path=srt_path,
                subtitled_video=video_path,
                zip_path=zip_path,
            )

            self.assertEqual(result, zip_path.resolve(strict=False))
            with ZipFile(result) as archive:
                self.assertEqual(
                    sorted(archive.namelist()),
                    ["lesson.srt", "lesson_subtitled.mp4"],
                )

    def test_zip_is_written_to_explicit_final_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            srt_path = temp_dir / "generated.srt"
            video_path = temp_dir / "lesson_subtitled.mp4"
            zip_path = temp_dir / "custom name.zip"
            srt_path.write_text("subtitle", encoding="utf-8")
            video_path.write_bytes(b"video")

            result = create_result_zip(
                original_video=Path("lesson.mp4"),
                srt_path=srt_path,
                subtitled_video=video_path,
                zip_path=zip_path,
            )

            self.assertEqual(result, zip_path.resolve(strict=False))
            self.assertTrue(zip_path.exists())

    @patch("subify.package.ZipFile")
    def test_zip_creation_wraps_zipfile_failures(self, zip_file) -> None:
        zip_file.side_effect = RuntimeError("compression unavailable")

        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            with self.assertRaises(PackagingError):
                create_result_zip(
                    original_video=Path("lesson.mp4"),
                    srt_path=temp_dir / "lesson.srt",
                    subtitled_video=temp_dir / "lesson_subtitled.mp4",
                    zip_path=temp_dir / "output" / "lesson_subify.zip",
                )


if __name__ == "__main__":
    unittest.main()

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
            srt_path.write_text("subtitle", encoding="utf-8")
            video_path.write_bytes(b"video")

            zip_path = create_result_zip(
                original_video=Path("lesson.mp4"),
                srt_path=srt_path,
                subtitled_video=video_path,
                output_dir=output_dir,
            )

            self.assertEqual(zip_path, output_dir / "lesson_subify.zip")
            with ZipFile(zip_path) as archive:
                self.assertEqual(
                    sorted(archive.namelist()),
                    ["lesson.srt", "lesson_subtitled.mp4"],
                )

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
                    output_dir=temp_dir / "output",
                )


if __name__ == "__main__":
    unittest.main()

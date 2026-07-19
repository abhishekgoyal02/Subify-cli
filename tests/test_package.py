import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

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

            with ZipFile(zip_path) as archive:
                self.assertEqual(
                    sorted(archive.namelist()),
                    ["lesson.srt", "lesson_subtitled.mp4"],
                )


if __name__ == "__main__":
    unittest.main()

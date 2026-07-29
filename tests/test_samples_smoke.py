import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from subify.pipeline import process_video


SAMPLE_VIDEO = Path("samples") / "5. [Dart] Functions - Part 1.mp4"


@unittest.skipUnless(
    os.environ.get("SUBIFY_RUN_SMOKE") == "1",
    "Set SUBIFY_RUN_SMOKE=1 to run sample video smoke tests.",
)
class SampleSmokeTests(unittest.TestCase):
    def test_process_sample_video_end_to_end(self) -> None:
        if not SAMPLE_VIDEO.exists():
            self.skipTest(f"Sample video missing: {SAMPLE_VIDEO}")
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            self.skipTest("FFmpeg and FFprobe are required for smoke tests.")
        if importlib.util.find_spec("faster_whisper") is None:
            self.skipTest("faster-whisper is required for smoke tests.")

        original_bytes = SAMPLE_VIDEO.read_bytes()
        with tempfile.TemporaryDirectory() as temp_dir_name:
            result = process_video(SAMPLE_VIDEO, output_dir=Path(temp_dir_name))

            self.assertIsNotNone(result.zip_path)
            self.assertTrue(result.zip_path.exists())
            self.assertEqual(result.zip_path.name, "5. [Dart] Functions - Part 1_subify.zip")
            with ZipFile(result.zip_path) as archive:
                self.assertEqual(
                    sorted(archive.namelist()),
                    [
                        "5. [Dart] Functions - Part 1.srt",
                        "5. [Dart] Functions - Part 1_subtitled.mp4",
                    ],
                )

        self.assertEqual(SAMPLE_VIDEO.read_bytes(), original_bytes)


if __name__ == "__main__":
    unittest.main()

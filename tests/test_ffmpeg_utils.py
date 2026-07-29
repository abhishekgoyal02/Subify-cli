import unittest
from pathlib import Path
from unittest.mock import patch

from subify.errors import FFmpegError
from subify.ffmpeg_utils import build_extract_audio_args, probe_video_duration


class FFmpegUtilsTests(unittest.TestCase):
    def test_extract_audio_command_uses_whisper_friendly_audio(self) -> None:
        args = build_extract_audio_args(Path("input.mp4"), Path("audio.wav"))

        self.assertIn("-ac", args)
        self.assertIn("1", args)
        self.assertIn("-ar", args)
        self.assertIn("16000", args)
        self.assertIn("pcm_s16le", args)
        self.assertNotIn("shell=True", args)

    @patch("subify.ffmpeg_utils.find_ffprobe", return_value="ffprobe")
    @patch("subify.ffmpeg_utils.subprocess.run")
    def test_probe_video_duration_reads_ffprobe_output(self, run, _find_ffprobe) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = "719.5\n"

        self.assertEqual(probe_video_duration(Path("lesson.mp4")), 719.5)

    @patch("subify.ffmpeg_utils.find_ffprobe", return_value="ffprobe")
    @patch("subify.ffmpeg_utils.subprocess.run")
    def test_probe_video_duration_wraps_invalid_output(self, run, _find_ffprobe) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = "N/A\n"

        with self.assertRaises(FFmpegError):
            probe_video_duration(Path("lesson.mp4"))


if __name__ == "__main__":
    unittest.main()

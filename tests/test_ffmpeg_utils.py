import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from subify.errors import FFmpegError
from subify.ffmpeg_utils import build_extract_audio_args, find_ffmpeg, find_ffprobe, probe_video_duration


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

    @patch("subify.ffmpeg_utils.managed_ffmpeg_paths", return_value=("managed-ffmpeg", "managed-ffprobe"))
    @patch("subify.ffmpeg_utils.shutil.which", return_value=None)
    def test_find_ffmpeg_uses_managed_binary_when_path_missing(self, _which, _managed_paths) -> None:
        self.assertEqual(find_ffmpeg(), "managed-ffmpeg")

    @patch("subify.ffmpeg_utils.managed_ffmpeg_paths", return_value=("managed-ffmpeg", "managed-ffprobe"))
    @patch("subify.ffmpeg_utils.shutil.which", return_value=None)
    def test_find_ffprobe_uses_managed_binary_when_path_missing(self, _which, _managed_paths) -> None:
        self.assertEqual(find_ffprobe(), "managed-ffprobe")

    @patch("subify.bootstrap.shutil.which", return_value=None)
    def test_bootstrap_fetches_static_ffmpeg_when_system_tools_missing(self, _which) -> None:
        from subify import bootstrap

        bootstrap.managed_ffmpeg_paths.cache_clear()
        run = Mock()
        run.get_or_fetch_platform_executables_else_raise.return_value = ("ffmpeg-bin", "ffprobe-bin")

        with patch.dict("sys.modules", {"static_ffmpeg": Mock(run=run)}):
            self.assertEqual(bootstrap.managed_ffmpeg_paths(), ("ffmpeg-bin", "ffprobe-bin"))


if __name__ == "__main__":
    unittest.main()

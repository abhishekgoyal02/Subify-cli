import unittest
from unittest import mock
import subprocess

from subify.embed import embed_subtitles


class EmbedTests(unittest.TestCase):
    @mock.patch("subify.embed.os.path.exists")
    def test_missing_video_raises_file_not_found(self, mock_exists):
        # Video doesn't exist
        mock_exists.side_effect = lambda path: path == "subs.srt"

        with self.assertRaises(FileNotFoundError):
            embed_subtitles("video.mp4", "subs.srt", "out.mp4")

    @mock.patch("subify.embed.os.path.exists")
    @mock.patch("subify.embed.os.path.isfile")
    def test_missing_subtitle_raises_file_not_found(self, mock_isfile, mock_exists):
        # Video exists, but subtitle doesn't
        mock_exists.side_effect = lambda path: path == "video.mp4"
        mock_isfile.return_value = True

        with self.assertRaises(FileNotFoundError):
            embed_subtitles("video.mp4", "subs.srt", "out.mp4")

    @mock.patch("subify.embed.os.path.exists", return_value=True)
    @mock.patch("subify.embed.os.path.isfile", return_value=True)
    @mock.patch("subify.embed.ffmpeg_utils.get_ffmpeg_path", return_value=None)
    def test_missing_ffmpeg_raises_file_not_found(self, mock_get_ffmpeg, mock_isfile, mock_exists):
        with self.assertRaises(FileNotFoundError):
            embed_subtitles("video.mp4", "subs.srt", "out.mp4")

    @mock.patch("subify.embed.os.path.exists", return_value=True)
    @mock.patch("subify.embed.os.path.isfile", return_value=True)
    @mock.patch("subify.embed.ffmpeg_utils.get_ffmpeg_path", return_value="/usr/bin/ffmpeg")
    @mock.patch("subify.embed.subprocess.run")
    def test_ffmpeg_command_construction(self, mock_run, mock_get_ffmpeg, mock_isfile, mock_exists):
        embed_subtitles(
            video_path=r"C:\path\to\video.mp4",
            subtitle_path=r"C:\path\to\subs.srt",
            output_path=r"C:\path\to\out.mp4"
        )

        mock_run.assert_called_once_with(
            [
                "/usr/bin/ffmpeg",
                "-y",
                "-i",
                r"C:\path\to\video.mp4",
                "-vf",
                "subtitles='C\\:/path/to/subs.srt'",
                r"C:\path\to\out.mp4",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

    @mock.patch("subify.embed.os.path.exists", return_value=True)
    @mock.patch("subify.embed.os.path.isfile", return_value=True)
    @mock.patch("subify.embed.ffmpeg_utils.get_ffmpeg_path", return_value="/usr/bin/ffmpeg")
    @mock.patch("subify.embed.subprocess.run", side_effect=subprocess.CalledProcessError(1, cmd=[], stderr="Error: filter graph failed"))
    def test_ffmpeg_failure_raises_runtime_error(self, mock_run, mock_get_ffmpeg, mock_isfile, mock_exists):
        with self.assertRaisesRegex(RuntimeError, "ffmpeg failed: Error: filter graph failed"):
            embed_subtitles("video.mp4", "subs.srt", "out.mp4")

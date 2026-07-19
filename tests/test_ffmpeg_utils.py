import unittest
from pathlib import Path

from subify.ffmpeg_utils import build_extract_audio_args


class FFmpegUtilsTests(unittest.TestCase):
    def test_extract_audio_command_uses_whisper_friendly_audio(self) -> None:
        args = build_extract_audio_args(Path("input.mp4"), Path("audio.wav"))

        self.assertIn("-ac", args)
        self.assertIn("1", args)
        self.assertIn("-ar", args)
        self.assertIn("16000", args)
        self.assertIn("pcm_s16le", args)
        self.assertNotIn("shell=True", args)


if __name__ == "__main__":
    unittest.main()

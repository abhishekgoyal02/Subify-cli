import unittest
from pathlib import Path

from subify.embed import build_embed_subtitles_args


class EmbedTests(unittest.TestCase):
    def test_embed_command_uses_paths_and_subtitle_filter(self) -> None:
        args = build_embed_subtitles_args(
            Path("input.mp4"),
            Path("captions.srt"),
            Path("subtitled.mp4"),
        )

        self.assertEqual(args[0], "-y")
        self.assertIn("input.mp4", args)
        self.assertIn("-vf", args)
        self.assertIn("subtitles=captions.srt", args)
        self.assertEqual(args[-1], "subtitled.mp4")


if __name__ == "__main__":
    unittest.main()

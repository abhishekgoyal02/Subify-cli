import unittest
from pathlib import Path
from unittest.mock import patch

from subify.errors import DependencyError, EmbeddingError, FFmpegError
from subify.embed import SubtitleStyle
from subify.embed import build_embed_subtitles_args
from subify.embed import build_force_style
from subify.embed import embed_subtitles


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
        self.assertTrue(any("subtitles=captions.srt" in arg for arg in args))
        self.assertEqual(args[-1], "subtitled.mp4")

    def test_subtitle_style_is_modern_and_minimal(self) -> None:
        style = build_force_style()

        self.assertIn("FontName=JetBrains Mono", style)
        self.assertIn("FontSize=18", style)
        self.assertIn("PrimaryColour=&H00FFFFFF", style)
        self.assertIn("OutlineColour=&H00000000", style)
        self.assertIn("BorderStyle=1", style)
        self.assertIn("Outline=1", style)
        self.assertIn("Shadow=0", style)
        self.assertIn("Bold=0", style)
        self.assertIn("Italic=0", style)
        self.assertIn("Alignment=2", style)
        self.assertIn("MarginV=36", style)

    def test_subtitle_style_caps_font_size_at_18(self) -> None:
        style = build_force_style(SubtitleStyle(font_size=24))

        self.assertIn("FontSize=18", style)
        self.assertNotIn("FontSize=24", style)

    def test_embed_filter_applies_centralized_force_style(self) -> None:
        args = build_embed_subtitles_args(
            Path("input.mp4"),
            Path("captions.srt"),
            Path("subtitled.mp4"),
        )

        video_filter = args[args.index("-vf") + 1]

        self.assertIn("force_style='", video_filter)
        self.assertIn(build_force_style(), video_filter)

    @patch("subify.embed.run_ffmpeg")
    def test_embed_wraps_ffmpeg_failures(self, run_ffmpeg) -> None:
        run_ffmpeg.side_effect = FFmpegError("ffmpeg failed")

        with self.assertRaises(EmbeddingError):
            embed_subtitles(Path("input.mp4"), Path("captions.srt"), Path("subtitled.mp4"))

    @patch("subify.embed.run_ffmpeg")
    def test_embed_preserves_dependency_errors(self, run_ffmpeg) -> None:
        run_ffmpeg.side_effect = DependencyError("missing ffmpeg")

        with self.assertRaises(DependencyError):
            embed_subtitles(Path("input.mp4"), Path("captions.srt"), Path("subtitled.mp4"))


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path
from unittest.mock import patch

from subify.errors import DependencyError, EmbeddingError, FFmpegError
from subify.embed import DEFAULT_SUBTITLE_STYLE
from subify.embed import SubtitleStyle
from subify.embed import build_embed_subtitles_args
from subify.embed import build_force_style
from subify.embed import build_subtitle_filter
from subify.embed import embed_subtitles
from subify.embed import select_subtitle_font


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
        self.assertTrue(any("subtitles=filename=captions.srt" in arg for arg in args))
        self.assertEqual(args[-1], "subtitled.mp4")

    def test_embed_uses_fast_video_preset_and_copies_audio(self) -> None:
        args = build_embed_subtitles_args(
            Path("input.mp4"),
            Path("captions.srt"),
            Path("subtitled.mp4"),
        )

        self.assertEqual(args[args.index("-preset") + 1], "veryfast")
        self.assertEqual(args[args.index("-c:a") + 1], "copy")

    def test_subtitle_filter_escapes_special_character_paths(self) -> None:
        filenames = [
            "My Video.srt",
            "5. [Dart] Functions - Part 1.srt",
            "video's subtitle.srt",
            "video (1080p).srt",
            "こんにちは.srt",
            "file,name=sample.srt",
        ]

        for filename in filenames:
            with self.subTest(filename=filename):
                subtitle_filter = build_subtitle_filter(Path(filename))

                self.assertTrue(subtitle_filter.startswith("subtitles=filename="))
                self.assertIn(":force_style=", subtitle_filter)

    def test_subtitle_filter_handles_windows_paths(self) -> None:
        subtitle_filter = build_subtitle_filter(
            Path(r"C:\Users\Aparna goyal\Downloads\5. [Dart] Functions - Part 1.srt")
        )

        self.assertIn("C\\\\:/Users/Aparna goyal/Downloads/5. \\[Dart\\] Functions - Part 1.srt", subtitle_filter)

    def test_subtitle_filter_escapes_apostrophes_inside_quoted_filename(self) -> None:
        subtitle_filter = build_subtitle_filter(Path("video's subtitle.srt"))

        self.assertIn("video\\\\\\'s subtitle.srt", subtitle_filter)

    def test_subtitle_filter_escapes_commas_and_equals_signs(self) -> None:
        subtitle_filter = build_subtitle_filter(Path("file,name=sample.srt"))

        self.assertIn("file\\,name\\=sample.srt", subtitle_filter)

    @patch("subify.embed._discover_available_font_names", return_value={"jetbrainsmonoregular"})
    def test_subtitle_style_is_modern_and_minimal(self, _discover_fonts) -> None:
        style = build_force_style()

        self.assertEqual(
            style,
            "Fontname=JetBrains Mono,"
            "FontSize=10,"
            "PrimaryColour=&H00E8E8E8,"
            "OutlineColour=&H80444444,"
            "BorderStyle=1,"
            "Outline=0.4,"
            "Shadow=0,"
            "Bold=0,"
            "Italic=0,"
            "Alignment=2,"
            "MarginL=12,"
            "MarginR=12,"
            "MarginV=12",
        )

    def test_subtitle_style_caps_font_size_at_10(self) -> None:
        style = build_force_style(SubtitleStyle(font_size=24))

        self.assertIn("FontSize=10", style)
        self.assertNotIn("FontSize=24", style)

    def test_subtitle_style_uses_one_concrete_font_not_css_fallback_chain(self) -> None:
        style = build_force_style(SubtitleStyle(font_name="Fira Code, monospace"))

        font_value = _force_style_value(style, "Fontname")

        self.assertEqual(font_value, "Fira Code")
        self.assertNotIn(",", font_value)

    def test_subtitle_style_remains_minimalist(self) -> None:
        style = build_force_style(SubtitleStyle(font_name="JetBrains Mono"))

        values = _force_style_values(style)

        self.assertEqual(values["PrimaryColour"], "&H00E8E8E8")
        self.assertEqual(values["OutlineColour"], "&H80444444")
        self.assertEqual(values["BorderStyle"], "1")
        self.assertEqual(values["Outline"], "0.4")
        self.assertEqual(values["Shadow"], "0")
        self.assertEqual(values["Bold"], "0")
        self.assertEqual(values["Italic"], "0")
        self.assertEqual(values["Alignment"], "2")
        self.assertLessEqual(int(values["FontSize"]), 10)
        self.assertEqual(int(values["MarginL"]), 12)
        self.assertEqual(int(values["MarginR"]), 12)
        self.assertEqual(int(values["MarginV"]), 12)

    @patch("subify.embed._discover_available_font_names")
    def test_font_selection_uses_first_detected_preferred_font(self, discover_fonts) -> None:
        discover_fonts.return_value = {"firacoderegular", "sourcecodeproregular"}

        self.assertEqual(select_subtitle_font(), "Fira Code")

    @patch("subify.embed._discover_available_font_names", return_value=set())
    def test_font_selection_falls_back_to_single_concrete_monospace_font(self, _discover_fonts) -> None:
        self.assertEqual(select_subtitle_font(), "Consolas")

    def test_default_subtitle_style_centralizes_minimal_embedding_values(self) -> None:
        self.assertEqual(DEFAULT_SUBTITLE_STYLE.font_size, 10)
        self.assertEqual(DEFAULT_SUBTITLE_STYLE.primary_color, "&H00E8E8E8")
        self.assertEqual(DEFAULT_SUBTITLE_STYLE.outline_color, "&H80444444")
        self.assertEqual(DEFAULT_SUBTITLE_STYLE.outline_width, 0.4)
        self.assertEqual(DEFAULT_SUBTITLE_STYLE.shadow, 0.0)
        self.assertEqual(DEFAULT_SUBTITLE_STYLE.bold, 0)
        self.assertEqual(DEFAULT_SUBTITLE_STYLE.italic, 0)
        self.assertEqual(DEFAULT_SUBTITLE_STYLE.alignment, 2)
        self.assertEqual(DEFAULT_SUBTITLE_STYLE.margin_vertical, 12)
        self.assertEqual(DEFAULT_SUBTITLE_STYLE.margin_left, 12)
        self.assertEqual(DEFAULT_SUBTITLE_STYLE.margin_right, 12)

    @patch("subify.embed._discover_available_font_names", return_value=set())
    def test_embed_filter_applies_centralized_force_style(self, _discover_fonts) -> None:
        args = build_embed_subtitles_args(
            Path("input.mp4"),
            Path("captions.srt"),
            Path("subtitled.mp4"),
        )

        video_filter = args[args.index("-vf") + 1]

        self.assertIn("force_style=", video_filter)
        self.assertIn("Fontname\\=Consolas", video_filter)
        self.assertIn("FontSize\\=10", video_filter)

    @patch("subify.embed._discover_available_font_names", return_value=set())
    def test_premium_subtitles_use_small_font_and_tight_margins(self, _discover_fonts) -> None:
        style = build_force_style(SubtitleStyle(font_name="Consolas"))
        values = _force_style_values(style)

        font_size = int(values["FontSize"])
        margin_left = int(values["MarginL"])
        margin_right = int(values["MarginR"])
        margin_vertical = int(values["MarginV"])

        self.assertLessEqual(font_size, 10, "Font size must be 10pt or smaller for premium look")
        self.assertLessEqual(margin_left, 12, "Left margin must be compact")
        self.assertLessEqual(margin_right, 12, "Right margin must be compact")
        self.assertLessEqual(margin_vertical, 12, "Vertical margin must be compact")

    @patch("subify.embed._discover_available_font_names", return_value=set())
    def test_premium_subtitles_use_subtle_outline_not_black_heavy(self, _discover_fonts) -> None:
        style = build_force_style(SubtitleStyle(font_name="Consolas"))
        values = _force_style_values(style)

        outline_width = float(values["Outline"])
        outline_color = values["OutlineColour"]

        self.assertLess(outline_width, 0.5, "Outline width must be thin and subtle")
        self.assertNotEqual(outline_color, "&H00000000", "Outline must not be pure black")
        self.assertIn("80", outline_color, "Outline should have subtle transparency")

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


def _force_style_values(style: str) -> dict[str, str]:
    return dict(part.split("=", maxsplit=1) for part in style.split(","))


def _force_style_value(style: str, key: str) -> str:
    return _force_style_values(style)[key]


if __name__ == "__main__":
    unittest.main()

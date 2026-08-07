import unittest

from subify.models import TranscriptSegment
from subify.srt_writer import format_srt_timestamp, render_srt, shape_subtitle_text


class SRTWriterTests(unittest.TestCase):
    def test_timestamp_formatting(self) -> None:
        self.assertEqual(format_srt_timestamp(3661.234), "01:01:01,234")

    def test_render_srt_keeps_segment_timestamps(self) -> None:
        content = render_srt(
            [
                TranscriptSegment(start=0.0, end=1.5, text="First line"),
                TranscriptSegment(start=2.0, end=3.0, text="Second line"),
            ]
        )

        self.assertIn("1\n00:00:00,000 --> 00:00:01,500\nFirst line", content)
        self.assertIn("2\n00:00:02,000 --> 00:00:03,000\nSecond line", content)

    def test_render_srt_skips_blank_segments_and_renumbers(self) -> None:
        content = render_srt(
            [
                TranscriptSegment(start=0.0, end=1.0, text="   "),
                TranscriptSegment(start=1.0, end=2.0, text="  Visible subtitle  "),
            ]
        )

        self.assertEqual(
            content,
            "1\n00:00:01,000 --> 00:00:02,000\nVisible subtitle\n",
        )

    def test_shape_subtitle_text_keeps_single_line_only(self) -> None:
        text = "This compact subtitle should wrap cleanly near the middle for a premium overlay"

        shaped = shape_subtitle_text(text, max_line_length=42)

        lines = shaped.splitlines()
        self.assertEqual(len(lines), 1, "Subtitles must be single-line, no wrapping")
        self.assertEqual(lines[0], text)

    def test_shape_subtitle_text_remains_single_line_even_with_punctuation(self) -> None:
        text = "Keep the first idea compact, then place the rest below"

        shaped = shape_subtitle_text(text, max_line_length=34)

        lines = shaped.splitlines()
        self.assertEqual(len(lines), 1, "Subtitles must remain single-line")
        self.assertEqual(shaped, text)

    def test_render_srt_uses_deterministic_single_line_wrapping(self) -> None:
        content = render_srt(
            [
                TranscriptSegment(
                    start=0.0,
                    end=2.0,
                    text="This compact subtitle should wrap cleanly near the middle for a premium overlay",
                )
            ]
        )

        subtitle_lines = content.splitlines()[2:3]

        self.assertEqual(len(subtitle_lines), 1, "Subtitles must be single-line in SRT output")
        self.assertEqual(
            subtitle_lines[0],
            "This compact subtitle should wrap cleanly near the middle for a premium overlay",
        )

    def test_shape_subtitle_text_enforces_single_line_no_newlines(self) -> None:
        text = "This is a very long subtitle that would normally wrap to multiple lines but should stay on a single line"

        shaped = shape_subtitle_text(text)

        self.assertNotIn("\n", shaped, "Subtitle text must not contain newlines")
        self.assertEqual(shaped.count("\n"), 0, "Must be single-line only")


if __name__ == "__main__":
    unittest.main()

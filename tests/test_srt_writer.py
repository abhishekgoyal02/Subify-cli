import unittest

from subify.srt_writer import format_srt_timestamp, render_srt
from subify.transcribe import TranscriptSegment


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


if __name__ == "__main__":
    unittest.main()

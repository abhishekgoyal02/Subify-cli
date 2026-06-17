import unittest
from types import SimpleNamespace
from subify.srt_writer import format_timestamp, generate_srt


class SrtWriterTests(unittest.TestCase):
    def test_format_timestamp_converts_correctly(self):
        self.assertEqual(format_timestamp(0), "00:00:00,000")
        self.assertEqual(format_timestamp(62.75), "00:01:02,750")
        self.assertEqual(format_timestamp(3665.2), "01:01:05,200")
        self.assertEqual(format_timestamp(-1.5), "00:00:00,000")
        self.assertEqual(format_timestamp(3599.999), "00:59:59,999")
        self.assertEqual(format_timestamp(3599.9999), "01:00:00,000")

    def test_generate_srt_with_valid_segments(self):
        segments = [
            SimpleNamespace(start=0.0, end=2.0, text="Welcome"),
            SimpleNamespace(start=2.0, end=5.0, text="This is Subify"),
        ]
        expected = (
            "1\n00:00:00,000 --> 00:00:02,000\nWelcome\n\n"
            "2\n00:00:02,000 --> 00:00:05,000\nThis is Subify\n"
        )
        self.assertEqual(generate_srt(segments), expected)

    def test_generate_srt_skips_empty_and_whitespace_segments(self):
        segments = [
            SimpleNamespace(start=0.0, end=2.0, text="Welcome"),
            SimpleNamespace(start=2.0, end=3.0, text="   "),
            SimpleNamespace(start=3.0, end=5.0, text=""),
            SimpleNamespace(start=5.0, end=7.0, text="This is Subify"),
        ]
        expected = (
            "1\n00:00:00,000 --> 00:00:02,000\nWelcome\n\n"
            "2\n00:00:05,000 --> 00:00:07,000\nThis is Subify\n"
        )
        self.assertEqual(generate_srt(segments), expected)

    def test_generate_srt_with_empty_input(self):
        self.assertEqual(generate_srt([]), "")

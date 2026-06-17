"""SRT subtitle generation and formatting helper."""

from typing import Iterable


def format_timestamp(seconds: float) -> str:
    """Convert a timestamp in seconds to the SRT format (HH:MM:SS,mmm)."""
    if seconds < 0:
        seconds = 0.0

    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    secs = total_seconds % 60
    total_minutes = total_seconds // 60
    mins = total_minutes % 60
    hours = total_minutes // 60

    return f"{hours:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def generate_srt(segments: Iterable) -> str:
    """Convert Whisper segments into SRT format.

    Skips segments whose text becomes empty after stripping whitespace.
    """
    srt_blocks = []
    index = 1
    for segment in segments:
        text = segment.text.strip() if segment.text else ""
        if not text:
            continue

        start_str = format_timestamp(segment.start)
        end_str = format_timestamp(segment.end)

        block = f"{index}\n{start_str} --> {end_str}\n{text}"
        srt_blocks.append(block)
        index += 1

    if not srt_blocks:
        return ""

    return "\n\n".join(srt_blocks) + "\n"

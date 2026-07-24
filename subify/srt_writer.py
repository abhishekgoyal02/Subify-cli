"""SRT subtitle generation."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .errors import SRTError
from .models import TranscriptSegment


def format_srt_timestamp(seconds: float) -> str:
    if seconds < 0:
        raise SRTError("SRT timestamps cannot be negative.")

    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def render_srt(segments: Iterable[TranscriptSegment]) -> str:
    blocks: list[str] = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        if segment.end < segment.start:
            raise SRTError("Segment end timestamp cannot be before start timestamp.")
        index = len(blocks) + 1
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{format_srt_timestamp(segment.start)} --> {format_srt_timestamp(segment.end)}",
                    text,
                ]
            )
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def write_srt(segments: Iterable[TranscriptSegment], output_path: Path) -> None:
    try:
        output_path.write_text(render_srt(segments), encoding="utf-8")
    except OSError as exc:
        raise SRTError(f"Unable to write SRT file: {exc}") from exc

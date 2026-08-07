"""SRT subtitle generation."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .errors import SRTError
from .models import TranscriptSegment

MAX_SUBTITLE_LINE_LENGTH = 42
MAX_SUBTITLE_LINES = 2


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
        subtitle_text = shape_subtitle_text(text)
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{format_srt_timestamp(segment.start)} --> {format_srt_timestamp(segment.end)}",
                    subtitle_text,
                ]
            )
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def shape_subtitle_text(
    text: str,
    *,
    max_line_length: int = MAX_SUBTITLE_LINE_LENGTH,
    max_lines: int = MAX_SUBTITLE_LINES,
) -> str:
    words = text.split()
    if not words:
        return ""
    if len(text) <= max_line_length:
        return text

    lines = _wrap_words(words, max_line_length=max_line_length, max_lines=max_lines)
    return "\n".join(lines)


def _wrap_words(words: list[str], *, max_line_length: int, max_lines: int) -> list[str]:
    if max_lines <= 1:
        return [" ".join(words)]

    line_count = min(max_lines, 2)
    split_index = _best_two_line_split(words, max_line_length)
    if split_index is None:
        split_index = _balanced_split(words)

    first = " ".join(words[:split_index])
    second = " ".join(words[split_index:])
    if line_count == 1 or not second:
        return [first]
    return [first, second]


def _best_two_line_split(words: list[str], max_line_length: int) -> int | None:
    best_index: int | None = None
    best_score: tuple[int, int] | None = None
    for index in range(1, len(words)):
        first = " ".join(words[:index])
        second = " ".join(words[index:])
        longest = max(len(first), len(second))
        if longest > max_line_length:
            continue
        punctuation_bonus = 0 if first[-1:] in {",", ".", "?", "!", ";", ":"} else 1
        balance = abs(len(first) - len(second))
        score = (punctuation_bonus, balance)
        if best_score is None or score < best_score:
            best_score = score
            best_index = index
    return best_index


def _balanced_split(words: list[str]) -> int:
    target = sum(len(word) for word in words) + len(words) - 1
    target //= 2
    best_index = 1
    best_distance: int | None = None
    for index in range(1, len(words)):
        first_length = len(" ".join(words[:index]))
        distance = abs(first_length - target)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_index = index
    return best_index


def write_srt(segments: Iterable[TranscriptSegment], output_path: Path) -> None:
    try:
        output_path.write_text(render_srt(segments), encoding="utf-8")
    except OSError as exc:
        raise SRTError(f"Unable to write SRT file: {exc}") from exc

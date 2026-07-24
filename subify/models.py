"""Shared domain models for Subify's reusable processing core."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass(frozen=True, slots=True)
class PipelineResult:
    zip_path: Path | None = None
    srt_path: Path | None = None
    video_path: Path | None = None
    segments: list[TranscriptSegment] = field(default_factory=list)
    elapsed_time: float = 0.0
    language: str = "en"
    warnings: tuple[str, ...] = ()

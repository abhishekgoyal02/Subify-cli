"""Subtitle embedding using FFmpeg."""

from __future__ import annotations

from pathlib import Path

from .errors import EmbeddingError
from .ffmpeg_utils import run_ffmpeg


def build_embed_subtitles_args(source_video: Path, srt_path: Path, output_video: Path) -> list[str]:
    subtitle_filter = f"subtitles={_escape_subtitle_path(srt_path)}"
    return [
        "-y",
        "-i",
        str(source_video),
        "-vf",
        subtitle_filter,
        "-c:a",
        "copy",
        str(output_video),
    ]


def embed_subtitles(source_video: Path, srt_path: Path, output_video: Path) -> None:
    try:
        run_ffmpeg(
            build_embed_subtitles_args(source_video, srt_path, output_video),
            description="embedding subtitles",
        )
    except Exception as exc:
        if isinstance(exc, EmbeddingError):
            raise
        raise EmbeddingError(str(exc)) from exc


def _escape_subtitle_path(path: Path) -> str:
    text = str(path).replace("\\", "/")
    return text.replace(":", "\\:").replace("'", "\\'")

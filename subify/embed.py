"""Subtitle embedding using FFmpeg."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .errors import EmbeddingError, FFmpegError
from .ffmpeg_utils import run_ffmpeg


PREFERRED_SUBTITLE_FONTS = (
    "JetBrains Mono",
    "Cascadia Code",
    "Fira Code",
    "IBM Plex Mono",
    "Source Code Pro",
)
FALLBACK_SUBTITLE_FONT = "monospace"
FONT_FILE_EXTENSIONS = {".ttf", ".otf", ".ttc", ".otc"}


@dataclass(frozen=True, slots=True)
class SubtitleStyle:
    font_name: str | None = None
    preferred_fonts: tuple[str, ...] = PREFERRED_SUBTITLE_FONTS
    fallback_font: str = FALLBACK_SUBTITLE_FONT
    font_size: int = 18
    primary_color: str = "&H00FFFFFF"
    outline_color: str = "&H00000000"
    border_style: int = 1
    outline_width: float = 1.0
    shadow: float = 0.0
    bold: int = 0
    italic: int = 0
    alignment: int = 2
    margin_left: int = 24
    margin_right: int = 24
    margin_vertical: int = 36


DEFAULT_SUBTITLE_STYLE = SubtitleStyle()


def build_embed_subtitles_args(source_video: Path, srt_path: Path, output_video: Path) -> list[str]:
    subtitle_filter = build_subtitle_filter(srt_path)
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
    except FFmpegError as exc:
        raise EmbeddingError(str(exc)) from exc


def build_subtitle_filter(srt_path: Path, style: SubtitleStyle = DEFAULT_SUBTITLE_STYLE) -> str:
    return (
        f"subtitles={_escape_subtitle_path(srt_path)}:"
        f"force_style='{build_force_style(style)}'"
    )


def build_force_style(style: SubtitleStyle = DEFAULT_SUBTITLE_STYLE) -> str:
    font_name = select_subtitle_font(style)
    values = {
        "Fontname": font_name,
        "FontSize": str(min(style.font_size, 18)),
        "PrimaryColour": style.primary_color,
        "OutlineColour": style.outline_color,
        "BorderStyle": str(style.border_style),
        "Outline": _format_ass_number(style.outline_width),
        "Shadow": _format_ass_number(style.shadow),
        "Bold": str(style.bold),
        "Italic": str(style.italic),
        "Alignment": str(style.alignment),
        "MarginL": str(style.margin_left),
        "MarginR": str(style.margin_right),
        "MarginV": str(style.margin_vertical),
    }
    return ",".join(f"{key}={value}" for key, value in values.items())


def select_subtitle_font(style: SubtitleStyle = DEFAULT_SUBTITLE_STYLE) -> str:
    if style.font_name:
        return style.font_name

    available_fonts = _discover_available_font_names(_font_search_dirs())
    for font_name in style.preferred_fonts:
        normalized = _normalize_font_name(font_name)
        if any(normalized in available for available in available_fonts):
            return font_name

    return style.fallback_font


def _escape_subtitle_path(path: Path) -> str:
    text = str(path).replace("\\", "/")
    return text.replace(":", "\\:").replace("'", "\\'")


def _format_ass_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return str(value)


def _discover_available_font_names(search_dirs: Iterable[Path]) -> set[str]:
    available: set[str] = set()
    for directory in search_dirs:
        if not directory.exists():
            continue
        try:
            font_files = (
                path
                for path in directory.rglob("*")
                if path.is_file() and path.suffix.lower() in FONT_FILE_EXTENSIONS
            )
            for path in font_files:
                available.add(_normalize_font_name(path.stem))
        except OSError:
            continue
    return available


def _font_search_dirs() -> tuple[Path, ...]:
    home = Path.home()
    windows_dir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    return (
        windows_dir / "Fonts",
        Path("/System/Library/Fonts"),
        Path("/Library/Fonts"),
        home / "Library" / "Fonts",
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        home / ".fonts",
        home / ".local" / "share" / "fonts",
    )


def _normalize_font_name(name: str) -> str:
    return "".join(character.lower() for character in name if character.isalnum())

"""FFmpeg discovery and execution helpers."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from .errors import DependencyError, FFmpegError


def find_ffmpeg() -> str:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise DependencyError("FFmpeg is not installed or is not on PATH.")
    return ffmpeg_path


def find_ffprobe() -> str:
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path is None:
        raise DependencyError("FFprobe is not installed or is not on PATH. Install FFmpeg first.")
    return ffprobe_path


def run_ffmpeg(args: Sequence[str], *, description: str) -> None:
    command = [find_ffmpeg(), *args]
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        raise FFmpegError(f"Unable to run FFmpeg while {description}: {exc}") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise FFmpegError(f"FFmpeg failed while {description}: {detail}")


def probe_video_duration(source_video: Path) -> float:
    command = [
        find_ffprobe(),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(source_video),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        raise FFmpegError(f"Unable to run FFprobe while reading video duration: {exc}") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise FFmpegError(f"FFprobe failed while reading video duration: {detail}")

    try:
        duration = float(completed.stdout.strip())
    except ValueError as exc:
        raise FFmpegError("FFprobe did not return a readable video duration.") from exc

    if duration < 0:
        raise FFmpegError("FFprobe returned an invalid negative video duration.")

    return duration


def build_extract_audio_args(source_video: Path, output_audio: Path) -> list[str]:
    return [
        "-y",
        "-i",
        str(source_video),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output_audio),
    ]


def extract_audio(source_video: Path, output_audio: Path) -> None:
    run_ffmpeg(
        build_extract_audio_args(source_video, output_audio),
        description="extracting mono 16 kHz audio",
    )

"""Subtitle embedding helper using FFmpeg."""

import os
import subprocess
from . import ffmpeg_utils


def embed_subtitles(video_path: str, subtitle_path: str, output_path: str) -> None:
    """Burn subtitles from `subtitle_path` into `video_path` and save as `output_path` using FFmpeg."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file '{video_path}' does not exist.")
    if not os.path.isfile(video_path):
        raise ValueError(f"Video path '{video_path}' is not a regular file.")

    if not os.path.exists(subtitle_path):
        raise FileNotFoundError(f"Subtitle file '{subtitle_path}' does not exist.")
    if not os.path.isfile(subtitle_path):
        raise ValueError(f"Subtitle path '{subtitle_path}' is not a regular file.")

    ffmpeg_path = ffmpeg_utils.get_ffmpeg_path()
    if not ffmpeg_path:
        raise FileNotFoundError(
            "ffmpeg not found. Install ffmpeg or set SUBIFY_FFMPEG_PATH to the ffmpeg executable."
        )

    # Format subtitles path for FFmpeg filter parser (Windows path compatibility)
    escaped_sub_path = subtitle_path.replace("\\", "/")
    escaped_sub_path = escaped_sub_path.replace(":", "\\:")
    escaped_sub_path = escaped_sub_path.replace("'", "'\\\\''")

    vf_argument = f"subtitles='{escaped_sub_path}'"

    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        video_path,
        "-vf",
        vf_argument,
        output_path,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        error_msg = stderr.splitlines()[-1] if stderr else str(exc)
        raise RuntimeError(f"ffmpeg failed: {error_msg}") from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to run FFmpeg: {exc}") from exc

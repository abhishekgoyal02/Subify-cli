"""FFmpeg utilities using subprocess.

Helpers call system ffmpeg. They raise clear exceptions on failure so callers
can present user-friendly messages.
"""
import os
import shutil
import subprocess
from typing import Optional


def _get_ffmpeg_path() -> Optional[str]:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

    env_path = os.environ.get("SUBIFY_FFMPEG_PATH", "").strip()
    if env_path and os.path.isfile(env_path) and os.access(env_path, os.X_OK):
        return env_path

    return None


def extract_audio(video_path: str, audio_out: str) -> None:
    """Extract audio from `video_path` and write to `audio_out` using ffmpeg.

    Raises FileNotFoundError when ffmpeg is not available and RuntimeError if
    ffmpeg exits with an error.
    """
    ffmpeg_path = _get_ffmpeg_path()
    if not ffmpeg_path:
        raise FileNotFoundError(
            "ffmpeg not found. Install ffmpeg or set SUBIFY_FFMPEG_PATH to the ffmpeg executable."
        )

    print(f"Using FFmpeg: {ffmpeg_path}")

    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        audio_out,
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        raise RuntimeError(
            f"ffmpeg failed: {stderr.splitlines()[-1] if stderr else 'unknown error'}"
        )

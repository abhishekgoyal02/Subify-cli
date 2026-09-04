"""Runtime bootstrap for Subify-managed local tools."""

from __future__ import annotations

import shutil
import sys
from functools import lru_cache

from . import ui
from .errors import DependencyError


@lru_cache(maxsize=1)
def managed_ffmpeg_paths() -> tuple[str, str]:
    """Return FFmpeg and FFprobe paths, downloading managed binaries if needed."""
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    if ffmpeg_path is not None and ffprobe_path is not None:
        return ffmpeg_path, ffprobe_path

    try:
        from static_ffmpeg import run
    except ImportError as exc:
        raise DependencyError(
            "Subify could not load its bundled FFmpeg installer. Reinstall with: pip install subify-cli"
        ) from exc

    try:
        ffmpeg_path, ffprobe_path = run.get_or_fetch_platform_executables_else_raise()
    except Exception as exc:
        raise DependencyError(f"Subify could not set up FFmpeg automatically: {exc}") from exc

    return str(ffmpeg_path), str(ffprobe_path)


def bootstrap_runtime_dependencies(*, announce: bool = False) -> None:
    """Prepare runtime dependencies that should work after pip install."""
    if system_ffmpeg_available():
        return

    if announce and sys.stdout.isatty():
        status = ui.PhaseStatus()
        status.start("Setting up Subify media tools")
        try:
            managed_ffmpeg_paths()
        except Exception as exc:
            status.fail("Could not set up Subify media tools", str(exc))
            raise
        status.complete("Subify media tools ready")
        return

    managed_ffmpeg_paths()


def system_ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

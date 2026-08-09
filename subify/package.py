"""Final ZIP packaging."""

from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from .errors import PackagingError


def create_result_zip(
    *,
    original_video: Path,
    srt_path: Path,
    subtitled_video: Path,
    zip_path: Path,
) -> Path:
    stem = original_video.stem

    try:
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
            archive.write(srt_path, arcname=f"{stem}.srt")
            archive.write(subtitled_video, arcname=f"{stem}_subtitled.mp4")
    except (BadZipFile, OSError, RuntimeError) as exc:
        raise PackagingError(f"Unable to create ZIP file: {exc}") from exc

    return zip_path.expanduser().resolve(strict=False)

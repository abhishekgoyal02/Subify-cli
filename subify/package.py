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
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = original_video.stem
    zip_path = output_dir / f"{stem}_subify.zip"

    try:
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
            archive.write(srt_path, arcname=f"{stem}.srt")
            archive.write(subtitled_video, arcname=f"{stem}_subtitled.mp4")
    except (BadZipFile, OSError, RuntimeError) as exc:
        raise PackagingError(f"Unable to create ZIP file: {exc}") from exc

    return zip_path

"""Reusable Subify processing pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import move
from tempfile import TemporaryDirectory
from typing import Callable

from .embed import embed_subtitles
from .errors import InputValidationError
from .ffmpeg_utils import extract_audio
from .package import create_result_zip
from .srt_writer import write_srt
from .transcribe import TranscriptSegment, transcribe_audio

ProgressCallback = Callable[[str, str], None]


@dataclass(frozen=True, slots=True)
class ProcessResult:
    zip_path: Path
    segments: list[TranscriptSegment]


@dataclass(frozen=True, slots=True)
class GenerateSRTResult:
    srt_path: Path
    segments: list[TranscriptSegment]


@dataclass(frozen=True, slots=True)
class EmbedResult:
    video_path: Path


def process_video(
    video_path: Path | str,
    *,
    output_dir: Path | str = "output",
    progress_callback: ProgressCallback | None = None,
) -> ProcessResult:
    source_video = validate_input_video(Path(video_path))
    resolved_output_dir = Path(output_dir)

    with TemporaryDirectory(prefix="subify-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        audio_path = temp_dir / "extracted_audio.wav"
        srt_path = temp_dir / f"{source_video.stem}.srt"
        subtitled_video = temp_dir / f"{source_video.stem}_subtitled.mp4"

        _run_stage("audio_extraction", progress_callback, extract_audio, source_video, audio_path)
        segments = _run_stage("english_transcription", progress_callback, transcribe_audio, audio_path)
        _run_stage("srt_generation", progress_callback, write_srt, segments, srt_path)
        _run_stage("subtitle_embedding", progress_callback, embed_subtitles, source_video, srt_path, subtitled_video)
        zip_path = _run_stage(
            "zip_packaging",
            progress_callback,
            create_result_zip,
            original_video=source_video,
            srt_path=srt_path,
            subtitled_video=subtitled_video,
            output_dir=resolved_output_dir,
        )

    return ProcessResult(zip_path=zip_path, segments=segments)


def generate_srt(
    video_path: Path | str,
    *,
    output_dir: Path | str = "output",
    progress_callback: ProgressCallback | None = None,
) -> GenerateSRTResult:
    source_video = validate_input_video(Path(video_path))
    resolved_output_dir = Path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    final_srt_path = resolved_output_dir / f"{source_video.stem}.srt"

    with TemporaryDirectory(prefix="subify-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        audio_path = temp_dir / "extracted_audio.wav"
        temporary_srt_path = temp_dir / f"{source_video.stem}.srt"

        _run_stage("audio_extraction", progress_callback, extract_audio, source_video, audio_path)
        segments = _run_stage("english_transcription", progress_callback, transcribe_audio, audio_path)
        _run_stage("srt_generation", progress_callback, write_srt, segments, temporary_srt_path)
        move(str(temporary_srt_path), str(final_srt_path))

    return GenerateSRTResult(srt_path=final_srt_path, segments=segments)


def embed_existing_subtitles(
    video_path: Path | str,
    subtitle_path: Path | str,
    *,
    output_dir: Path | str = "output",
    progress_callback: ProgressCallback | None = None,
) -> EmbedResult:
    source_video = validate_input_video(Path(video_path))
    source_srt = validate_input_file(Path(subtitle_path), label="Subtitle file")
    resolved_output_dir = Path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    final_video_path = resolved_output_dir / f"{source_video.stem}_subtitled.mp4"

    _emit(progress_callback, "input_validation", "start")
    _emit(progress_callback, "input_validation", "complete")

    with TemporaryDirectory(prefix="subify-", dir=resolved_output_dir) as temp_dir_name:
        temporary_video_path = Path(temp_dir_name) / final_video_path.name
        _run_stage(
            "subtitle_embedding",
            progress_callback,
            embed_subtitles,
            source_video,
            source_srt,
            temporary_video_path,
        )
        temporary_video_path.replace(final_video_path)

    return EmbedResult(video_path=final_video_path)


def validate_input_video(video_path: Path) -> Path:
    return validate_input_file(video_path, label="Input file")


def validate_input_file(file_path: Path, *, label: str) -> Path:
    try:
        resolved = file_path.expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise InputValidationError(f"{label} does not exist: {file_path}") from exc
    except OSError as exc:
        raise InputValidationError(f"Unable to access {label.lower()}: {file_path}") from exc

    if resolved.is_dir():
        raise InputValidationError(f"{label} is a directory: {resolved}")
    if not resolved.is_file():
        raise InputValidationError(f"{label} is not a file: {resolved}")

    try:
        with resolved.open("rb"):
            pass
    except OSError as exc:
        raise InputValidationError(f"{label} cannot be read: {resolved}") from exc

    return resolved


def _run_stage(stage: str, callback: ProgressCallback | None, function, *args, **kwargs):
    _emit(callback, stage, "start")
    result = function(*args, **kwargs)
    _emit(callback, stage, "complete")
    return result


def _emit(callback: ProgressCallback | None, stage: str, status: str) -> None:
    if callback is not None:
        callback(stage, status)

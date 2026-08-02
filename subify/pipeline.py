"""Reusable Subify processing pipeline."""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path
from shutil import move
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Callable

from .embed import embed_subtitles
from .errors import DependencyError, EmbeddingError, InputValidationError, SRTError
from .ffmpeg_utils import extract_audio, find_ffmpeg, find_ffprobe, probe_video_duration
from .models import PipelineResult
from .package import create_result_zip
from .srt_writer import write_srt
from .transcribe import DEFAULT_LANGUAGE, transcribe_audio

ProgressEvent = tuple[str, str]
ProgressCallback = Callable[[ProgressEvent], None]

ProcessResult = PipelineResult
GenerateSRTResult = PipelineResult
EmbedResult = PipelineResult

MAX_SUPPORTED_VIDEO_DURATION_SECONDS = 12 * 60
MIN_TEMP_SPACE_BYTES = 250 * 1024 * 1024
SUPPORTED_VIDEO_SUFFIXES = {".mp4"}


def process_video(
    video_path: Path | str,
    *,
    output_dir: Path | str = "output",
    progress_callback: ProgressCallback | None = None,
) -> ProcessResult:
    started_at = perf_counter()
    source_video = _run_stage(
        "input_validation",
        progress_callback,
        validate_input_video,
        Path(video_path),
    )
    _run_stage("dependency_validation", progress_callback, validate_runtime_dependencies, require_whisper=True)
    _run_stage("duration_validation", progress_callback, validate_supported_duration, source_video)
    resolved_output_dir = _run_stage(
        "disk_space_validation",
        progress_callback,
        validate_output_and_temporary_space,
        source_video,
        Path(output_dir),
    )

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

    return ProcessResult(
        zip_path=_normalize_path(zip_path),
        segments=segments,
        elapsed_time=_elapsed_since(started_at),
        language=DEFAULT_LANGUAGE,
    )


def generate_srt(
    video_path: Path | str,
    *,
    output_dir: Path | str = "output",
    progress_callback: ProgressCallback | None = None,
) -> GenerateSRTResult:
    started_at = perf_counter()
    source_video = _run_stage(
        "input_validation",
        progress_callback,
        validate_input_video,
        Path(video_path),
    )
    _run_stage("dependency_validation", progress_callback, validate_runtime_dependencies, require_whisper=True)
    _run_stage("duration_validation", progress_callback, validate_supported_duration, source_video)
    resolved_output_dir = _run_stage(
        "disk_space_validation",
        progress_callback,
        validate_output_and_temporary_space,
        source_video,
        Path(output_dir),
    )
    final_srt_path = resolved_output_dir / f"{source_video.stem}.srt"

    with TemporaryDirectory(prefix="subify-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        audio_path = temp_dir / "extracted_audio.wav"
        temporary_srt_path = temp_dir / f"{source_video.stem}.srt"

        _run_stage("audio_extraction", progress_callback, extract_audio, source_video, audio_path)
        segments = _run_stage("english_transcription", progress_callback, transcribe_audio, audio_path)
        _run_stage("srt_generation", progress_callback, write_srt, segments, temporary_srt_path)
        try:
            move(str(temporary_srt_path), str(final_srt_path))
        except OSError as exc:
            raise SRTError(f"Unable to write final SRT file: {exc}") from exc

    return GenerateSRTResult(
        srt_path=_normalize_path(final_srt_path),
        segments=segments,
        elapsed_time=_elapsed_since(started_at),
        language=DEFAULT_LANGUAGE,
    )


def embed_existing_subtitles(
    video_path: Path | str,
    subtitle_path: Path | str,
    *,
    output_dir: Path | str = "output",
    progress_callback: ProgressCallback | None = None,
) -> EmbedResult:
    started_at = perf_counter()
    source_video, source_srt = _run_stage(
        "input_validation",
        progress_callback,
        _validate_embed_inputs,
        Path(video_path),
        Path(subtitle_path),
    )
    _run_stage("dependency_validation", progress_callback, validate_runtime_dependencies, require_whisper=False)
    _run_stage("duration_validation", progress_callback, validate_supported_duration, source_video)
    resolved_output_dir = _run_stage(
        "disk_space_validation",
        progress_callback,
        validate_output_and_temporary_space,
        source_video,
        Path(output_dir),
    )
    final_video_path = resolved_output_dir / f"{source_video.stem}_subtitled.mp4"

    with TemporaryDirectory(prefix="subify-") as temp_dir_name:
        temporary_video_path = Path(temp_dir_name) / final_video_path.name
        _run_stage(
            "subtitle_embedding",
            progress_callback,
            embed_subtitles,
            source_video,
            source_srt,
            temporary_video_path,
        )
        try:
            move(str(temporary_video_path), str(final_video_path))
        except OSError as exc:
            raise EmbeddingError(f"Unable to write subtitled video: {exc}") from exc

    return EmbedResult(
        video_path=_normalize_path(final_video_path),
        elapsed_time=_elapsed_since(started_at),
        language=DEFAULT_LANGUAGE,
    )


def validate_input_video(video_path: Path) -> Path:
    source_video = validate_input_file(video_path, label="Input file")
    if source_video.suffix.lower() not in SUPPORTED_VIDEO_SUFFIXES:
        raise InputValidationError("Only .mp4 videos are supported in this version.")
    return source_video


def _validate_embed_inputs(video_path: Path, subtitle_path: Path) -> tuple[Path, Path]:
    return (
        validate_input_video(video_path),
        validate_input_file(subtitle_path, label="Subtitle file"),
    )


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


def validate_runtime_dependencies(*, require_whisper: bool) -> None:
    validate_python_runtime()
    find_ffmpeg()
    find_ffprobe()
    validate_importable_dependency("rich", "Rich is not installed. Install project dependencies first.")
    if require_whisper:
        validate_importable_dependency(
            "faster_whisper",
            "faster-whisper is not installed. Install project dependencies first.",
        )


def dependency_status(*, include_whisper: bool) -> tuple[bool, bool]:
    ffmpeg_ready = _dependency_ready(_validate_ffmpeg_tools)
    whisper_ready = True
    if include_whisper:
        whisper_ready = _dependency_ready(
            lambda: validate_importable_dependency(
                "faster_whisper",
                "faster-whisper is not installed. Install project dependencies first.",
            )
        )
    return ffmpeg_ready, whisper_ready


def validate_python_runtime() -> None:
    if sys.version_info < (3, 11):
        raise DependencyError("Python 3.11 or newer is required.")


def validate_importable_dependency(module_name: str, error_message: str) -> None:
    try:
        available = importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        available = False
    if not available:
        raise DependencyError(error_message)


def _validate_ffmpeg_tools() -> None:
    find_ffmpeg()
    find_ffprobe()


def _dependency_ready(check) -> bool:
    try:
        check()
    except DependencyError:
        return False
    return True


def validate_supported_duration(video_path: Path) -> float:
    duration = probe_video_duration(video_path)
    if duration > MAX_SUPPORTED_VIDEO_DURATION_SECONDS:
        minutes = duration / 60
        raise InputValidationError(
            f"Input video is {minutes:.1f} minutes long. "
            "The current supported limit is 12 minutes."
        )
    return duration


def validate_output_and_temporary_space(source_video: Path, output_dir: Path) -> Path:
    resolved_output_dir = validate_output_directory(output_dir)
    validate_temporary_space(source_video, resolved_output_dir)
    return resolved_output_dir


def validate_output_directory(output_dir: Path) -> Path:
    try:
        resolved = output_dir.expanduser().resolve(strict=False)
        if resolved.exists() and not resolved.is_dir():
            raise InputValidationError(
                f"Output path is not a directory and cannot be used: {resolved}"
            )
        resolved.mkdir(parents=True, exist_ok=True)
    except InputValidationError:
        raise
    except OSError as exc:
        raise InputValidationError(f"Output directory cannot be created: {output_dir}") from exc

    if not resolved.is_dir():
        raise InputValidationError(f"Output path is not a directory and cannot be used: {resolved}")

    marker = resolved / ".subify-write-test"
    try:
        marker.write_text("", encoding="utf-8")
    except OSError as exc:
        raise InputValidationError(f"Output directory is not writable: {resolved}") from exc
    finally:
        try:
            marker.unlink(missing_ok=True)
        except OSError:
            pass

    return resolved


def validate_temporary_space(source_video: Path, output_dir: Path) -> None:
    try:
        source_size = source_video.stat().st_size
    except OSError as exc:
        raise InputValidationError(f"Unable to inspect input file size: {source_video}") from exc

    required_bytes = max(source_size * 2, MIN_TEMP_SPACE_BYTES)
    for label, location in (
        ("temporary", Path(tempfile.gettempdir())),
        ("output", output_dir),
    ):
        try:
            usage = shutil.disk_usage(location)
        except OSError:
            continue
        if usage.free < required_bytes:
            required_mb = required_bytes / (1024 * 1024)
            available_mb = usage.free / (1024 * 1024)
            raise InputValidationError(
                f"Not enough {label} disk space. "
                f"Need about {required_mb:.0f} MB free; found {available_mb:.0f} MB."
            )


def _run_stage(stage: str, callback: ProgressCallback | None, function, *args, **kwargs):
    _emit(callback, stage, "start")
    result = function(*args, **kwargs)
    _emit(callback, stage, "complete")
    return result


def _emit(callback: ProgressCallback | None, stage: str, status: str) -> None:
    if callback is not None:
        callback((stage, status))


def _elapsed_since(started_at: float) -> float:
    return perf_counter() - started_at


def _normalize_path(path: Path | None) -> Path | None:
    if path is None:
        return None
    return path.expanduser().resolve(strict=False)

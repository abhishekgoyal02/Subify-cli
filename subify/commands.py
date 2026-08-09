from __future__ import annotations

import sys
from pathlib import Path

from . import ui
from .errors import SubifyError
from .models import TranscriptSegment
from .pipeline import dependency_status, embed_existing_subtitles, generate_srt, process_video

STAGE_LABELS = {
    "input_validation": "Input validation",
    "dependency_validation": "Dependency validation",
    "duration_validation": "Duration validation",
    "disk_space_validation": "Disk space validation",
    "audio_extraction": "Audio extraction",
    "english_transcription": "English transcription",
    "srt_generation": "SRT generation",
    "subtitle_embedding": "Subtitle embedding",
    "zip_packaging": "ZIP packaging",
}


def process_command(video_path: Path, output_dir: Path | None, show_transcript: bool) -> int:
    _print_dependency_status(include_whisper=True)
    progress = _ProgressPrinter()
    try:
        result = process_video(video_path, output_dir=output_dir, progress_callback=progress)
    except SubifyError as exc:
        _render_expected_error(exc)
        return 1
    except KeyboardInterrupt:
        _render_expected_error(SubifyError("Processing interrupted."))
        return 1
    except Exception:
        _render_expected_error(SubifyError("Unexpected error. Processing aborted."))
        return 1

    if show_transcript:
        _print_transcript(result.segments)
    ui.render_success("Processing complete", result.zip_path)
    return 0


def generate_srt_command(video_path: Path, output_dir: Path | None, show_transcript: bool) -> int:
    _print_dependency_status(include_whisper=True)
    progress = _ProgressPrinter()
    try:
        result = generate_srt(video_path, output_dir=output_dir, progress_callback=progress)
    except SubifyError as exc:
        _render_expected_error(exc)
        return 1
    except KeyboardInterrupt:
        _render_expected_error(SubifyError("Processing interrupted."))
        return 1
    except Exception:
        _render_expected_error(SubifyError("Unexpected error. Processing aborted."))
        return 1

    if show_transcript:
        _print_transcript(result.segments)
    ui.render_success("SRT generated", result.srt_path)
    return 0


def embed_command(video_path: Path, subtitle_path: Path, output_dir: Path | None) -> int:
    _print_dependency_status(include_whisper=False)
    progress = _ProgressPrinter()
    try:
        result = embed_existing_subtitles(
            video_path,
            subtitle_path,
            output_dir=output_dir,
            progress_callback=progress,
        )
    except SubifyError as exc:
        _render_expected_error(exc)
        return 1
    except KeyboardInterrupt:
        _render_expected_error(SubifyError("Processing interrupted."))
        return 1
    except Exception:
        _render_expected_error(SubifyError("Unexpected error. Processing aborted."))
        return 1

    ui.render_success("Subtitle embedding complete", result.video_path)
    return 0


class _ProgressPrinter:
    def __call__(self, event: tuple[str, str]) -> None:
        stage, status = event
        label = STAGE_LABELS.get(stage, stage.replace("_", " ").title())
        ui.render_stage(label, status)


def _print_dependency_status(*, include_whisper: bool) -> None:
    ffmpeg_ready, whisper_ready = dependency_status(include_whisper=include_whisper)
    ui.render_dependency_status(
        ffmpeg_ready=ffmpeg_ready,
        whisper_ready=whisper_ready,
        include_whisper=include_whisper,
    )


def _print_transcript(segments: list[TranscriptSegment]) -> None:
    ui.render_transcript_header()
    for segment in segments:
        ui.print_message(f"{segment.start:.2f}-{segment.end:.2f}  {segment.text}")


def _render_expected_error(exc: SubifyError) -> None:
    message = str(exc)
    try:
        ui.render_error(message)
    except Exception:
        print(f"Subify error: {message}", file=sys.stderr)

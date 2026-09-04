from __future__ import annotations

import sys
from pathlib import Path

from . import ui
from .doctor import doctor_command
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

PROCESS_PHASES = {
    "input_validation": ("Looking over your video", "disk_space_validation", "Could not prepare the video"),
    "dependency_validation": ("Looking over your video", "disk_space_validation", "Could not prepare the video"),
    "duration_validation": ("Looking over your video", "disk_space_validation", "Could not prepare the video"),
    "disk_space_validation": ("Looking over your video", "disk_space_validation", "Could not prepare the video"),
    "audio_extraction": ("Extracting .srt from audio", "srt_generation", "Could not generate subtitles"),
    "english_transcription": ("Extracting .srt from audio", "srt_generation", "Could not generate subtitles"),
    "srt_generation": ("Extracting .srt from audio", "srt_generation", "Could not generate subtitles"),
    "subtitle_embedding": ("Burning subtitles into video", "subtitle_embedding", "Could not burn subtitles"),
    "zip_packaging": ("Preparing the .zip file", "zip_packaging", "Could not prepare the .zip file"),
}

GENERATE_SRT_PHASES = {
    "input_validation": ("Looking over your video", "disk_space_validation", "Could not prepare the video"),
    "dependency_validation": ("Looking over your video", "disk_space_validation", "Could not prepare the video"),
    "duration_validation": ("Looking over your video", "disk_space_validation", "Could not prepare the video"),
    "disk_space_validation": ("Looking over your video", "disk_space_validation", "Could not prepare the video"),
    "audio_extraction": ("Listening to the audio", "english_transcription", "Could not read the audio"),
    "english_transcription": ("Listening to the audio", "english_transcription", "Could not generate subtitles"),
    "srt_generation": ("Writing the .srt file", "srt_generation", "Could not write the .srt file"),
}


def process_command(video_path: Path, output_dir: Path | None, show_transcript: bool) -> int:
    progress = _PhaseProgressPrinter(PROCESS_PHASES, default_failure="Could not prepare the video")
    try:
        result = process_video(video_path, output_dir=output_dir, progress_callback=progress)
    except SubifyError as exc:
        progress.fail(str(exc))
        return 1
    except KeyboardInterrupt:
        progress.fail("Processing interrupted.")
        return 1
    except Exception:
        progress.fail("Unexpected error. Processing aborted.")
        return 1
    finally:
        progress.stop_if_active()

    if show_transcript:
        _print_transcript(result.segments)
    ui.render_output_location(result.zip_path)
    return 0


def generate_srt_command(video_path: Path, output_dir: Path | None, show_transcript: bool) -> int:
    progress = _PhaseProgressPrinter(GENERATE_SRT_PHASES, default_failure="Could not generate subtitles")
    try:
        result = generate_srt(video_path, output_dir=output_dir, progress_callback=progress)
    except SubifyError as exc:
        progress.fail(str(exc))
        return 1
    except KeyboardInterrupt:
        progress.fail("Processing interrupted.")
        return 1
    except Exception:
        progress.fail("Unexpected error. Processing aborted.")
        return 1
    finally:
        progress.stop_if_active()

    if show_transcript:
        _print_transcript(result.segments)
    ui.render_output_location(result.srt_path)
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


class _PhaseProgressPrinter:
    def __init__(
        self,
        phases: dict[str, tuple[str, str, str]],
        *,
        default_failure: str,
    ) -> None:
        self._phases = phases
        self._status = ui.PhaseStatus()
        self._active_title: str | None = None
        self._failure_title = default_failure
        self._completed_titles: set[str] = set()

    def __call__(self, event: tuple[str, str]) -> None:
        stage, status = event
        phase = self._phases.get(stage)
        if phase is None:
            return

        title, completes_on, failure_title = phase
        self._failure_title = failure_title
        if status == "start":
            if title not in self._completed_titles:
                self._active_title = title
                self._status.start(title)
            return

        if status == "complete" and stage == completes_on and title not in self._completed_titles:
            self._status.complete(title)
            self._completed_titles.add(title)
            self._active_title = None

    def fail(self, detail: str) -> None:
        title = self._failure_title
        self._status.fail(title, detail)
        self._active_title = None

    def stop_if_active(self) -> None:
        if self._active_title is not None:
            self._status.stop()
            self._active_title = None


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

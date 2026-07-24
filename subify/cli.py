"""Command-line interface for Subify."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from typing import Sequence

from . import __version__
from .errors import SubifyError
from .ffmpeg_utils import find_ffmpeg
from .models import TranscriptSegment
from .pipeline import embed_existing_subtitles, generate_srt, process_video
from .ui import (
    print_message,
    render_dependency_status,
    render_error,
    render_stage,
    render_success,
    render_transcript_header,
    render_welcome,
)

STAGE_LABELS = {
    "input_validation": "Input validation",
    "audio_extraction": "Audio extraction",
    "english_transcription": "English transcription",
    "srt_generation": "SRT generation",
    "subtitle_embedding": "Subtitle embedding",
    "zip_packaging": "ZIP packaging",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="subify",
        description=(
            "Generate English subtitles, burn subtitles into videos, and package "
            "subtitle outputs."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Subify-CLI {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")
    process_parser = subparsers.add_parser(
        "process",
        help="Run the full English subtitle pipeline and create a ZIP.",
        description="Generate English SRT subtitles, burn them into the video, and create a ZIP.",
    )
    process_parser.add_argument("video_path", help="Path to the source video.")
    process_parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory where the final ZIP will be written. Defaults to output/.",
    )
    process_parser.add_argument(
        "--show-transcript",
        action="store_true",
        help="Print generated English transcript segments after processing.",
    )

    srt_parser = subparsers.add_parser(
        "generate-srt",
        help="Generate an English SRT file without embedding subtitles.",
        description="Extract audio, transcribe English speech, and write an SRT file.",
    )
    srt_parser.add_argument("video_path", help="Path to the source video.")
    srt_parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory where the SRT file will be written. Defaults to output/.",
    )
    srt_parser.add_argument(
        "--show-transcript",
        action="store_true",
        help="Print generated English transcript segments after SRT generation.",
    )

    embed_parser = subparsers.add_parser(
        "embed",
        help="Burn an existing SRT file into a video.",
        description="Burn an existing subtitle file into a video without Whisper transcription.",
    )
    embed_parser.add_argument("video_path", help="Path to the source video.")
    embed_parser.add_argument("subtitle_path", help="Path to an existing SRT subtitle file.")
    embed_parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory where the subtitled MP4 will be written. Defaults to output/.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(argv) if argv is not None else None
    if args_list == []:
        render_welcome(__version__, Path.cwd())
        return 0

    parser = build_parser()
    args = parser.parse_args(args_list)

    if args.command == "process":
        return _process_command(Path(args.video_path), Path(args.output_dir), args.show_transcript)
    if args.command == "generate-srt":
        return _generate_srt_command(Path(args.video_path), Path(args.output_dir), args.show_transcript)
    if args.command == "embed":
        return _embed_command(Path(args.video_path), Path(args.subtitle_path), Path(args.output_dir))

    render_welcome(__version__, Path.cwd())
    return 0


def _process_command(video_path: Path, output_dir: Path, show_transcript: bool) -> int:
    _print_dependency_status(include_whisper=True)
    progress = _ProgressPrinter()
    try:
        result = process_video(video_path, output_dir=output_dir, progress_callback=progress)
    except SubifyError as exc:
        _print_error(exc)
        return 1

    if show_transcript:
        _print_transcript(result.segments)
    _print_success("Processing complete", result.zip_path)
    return 0


def _generate_srt_command(video_path: Path, output_dir: Path, show_transcript: bool) -> int:
    _print_dependency_status(include_whisper=True)
    progress = _ProgressPrinter()
    try:
        result = generate_srt(video_path, output_dir=output_dir, progress_callback=progress)
    except SubifyError as exc:
        _print_error(exc)
        return 1

    if show_transcript:
        _print_transcript(result.segments)
    _print_success("SRT generated", result.srt_path)
    return 0


def _embed_command(video_path: Path, subtitle_path: Path, output_dir: Path) -> int:
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
        _print_error(exc)
        return 1

    _print_success("Subtitle embedding complete", result.video_path)
    return 0


class _ProgressPrinter:
    def __call__(self, stage: str, status: str) -> None:
        label = STAGE_LABELS.get(stage, stage.replace("_", " ").title())
        render_stage(label, status)


def _print_dependency_status(*, include_whisper: bool) -> None:
    ffmpeg_ready = _dependency_ready(find_ffmpeg)
    whisper_ready = importlib.util.find_spec("faster_whisper") is not None
    render_dependency_status(
        ffmpeg_ready=ffmpeg_ready,
        whisper_ready=whisper_ready,
        include_whisper=include_whisper,
    )


def _dependency_ready(check) -> bool:
    try:
        check()
    except SubifyError:
        return False
    return True


def _print_transcript(segments: list[TranscriptSegment]) -> None:
    render_transcript_header()
    for segment in segments:
        print_message(f"{segment.start:.2f}-{segment.end:.2f}  {segment.text}")


def _print_success(message: str, output_path: Path) -> None:
    render_success(message, output_path)


def _print_error(exc: SubifyError) -> None:
    render_error(str(exc))

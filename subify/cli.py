"""Command-line interface for Subify."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .commands import embed_command, generate_srt_command, process_command
from .shell import start_shell


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
        default=None,
        help="Directory where the final ZIP will be written. Default: user's Downloads/Subify folder.",
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
        default=None,
        help="Directory where the SRT file will be written. Default: user's Downloads/Subify folder.",
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
        default=None,
        help="Directory where the subtitled MP4 will be written. Default: user's Downloads/Subify folder.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(argv) if argv is not None else list(sys.argv[1:])
    if args_list == []:
        return start_shell(run_command)

    return run_command(args_list)


def run_command(argv: Sequence[str]) -> int:
    args_list = list(argv)

    parser = build_parser()
    args = parser.parse_args(args_list)

    if args.command == "process":
        output_dir = Path(args.output_dir) if args.output_dir is not None else None
        return process_command(Path(args.video_path), output_dir, args.show_transcript)
    if args.command == "generate-srt":
        output_dir = Path(args.output_dir) if args.output_dir is not None else None
        return generate_srt_command(Path(args.video_path), output_dir, args.show_transcript)
    if args.command == "embed":
        output_dir = Path(args.output_dir) if args.output_dir is not None else None
        return embed_command(Path(args.video_path), Path(args.subtitle_path), output_dir)

    parser.print_help()
    return 0

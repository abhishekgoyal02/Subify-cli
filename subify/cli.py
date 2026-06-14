import argparse
import os
import sys

from .banner import display_startup_banner
from . import ffmpeg_utils
from . import transcribe


def _ensure_exists(path: str, label: str = "File") -> None:
    """Exit with a clear error if `path` does not exist."""
    if not os.path.exists(path):
        print(f"Error: {label} '{path}' does not exist.")
        sys.exit(1)


def _generate_srt(args):
    _ensure_exists(args.input)

    try:
        print("Starting audio extraction...")
        audio_path = "audio.wav"
        ffmpeg_utils.extract_audio(args.input, audio_out=audio_path)
        print("Audio extracted successfully.")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error during audio extraction: {e}")
        sys.exit(1)

    try:
        print("Starting transcription...")
        transcript = transcribe.transcribe_audio(audio_path, model_name="base")
        print()
        if transcript.strip():
            print(transcript)
        print()
        print("Transcription completed.")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error during transcription: {e}")
        sys.exit(1)


def _embed(args):
    _ensure_exists(args.video, "Video")
    _ensure_exists(args.srt, "Subtitle file")
    print(f"[subify] embed (placeholder) video={args.video} srt={args.srt}")


def _process(args):
    _ensure_exists(args.input)
    print(f"[subify] process (placeholder) input={args.input}")


def main():
    display_startup_banner()

    parser = argparse.ArgumentParser(
        prog="subify",
        description="Subify CLI - transcript generation utilities (placeholders remain)",
    )
    parser.add_argument("--version", action="version", version="0.1.0")

    subparsers = parser.add_subparsers(dest="command")

    p_gen = subparsers.add_parser("generate-srt", help="Generate transcript from video")
    p_gen.add_argument("input", help="Input video file")
    p_gen.set_defaults(func=_generate_srt)

    p_embed = subparsers.add_parser("embed", help="Embed .srt into video (placeholder)")
    p_embed.add_argument("video", help="Input video file")
    p_embed.add_argument("srt", help="Subtitle file (.srt)")
    p_embed.set_defaults(func=_embed)

    p_proc = subparsers.add_parser("process", help="Run full pipeline (placeholder)")
    p_proc.add_argument("input", help="Input video file")
    p_proc.set_defaults(func=_process)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
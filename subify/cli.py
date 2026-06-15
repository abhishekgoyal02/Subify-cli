import argparse
import os
import sys
import tempfile

from .banner import display_startup_banner
from . import ffmpeg_utils, transcribe


def _ensure_readable_file(path: str, label: str = "File") -> None:
    """Exit with a clear error unless `path` is a readable regular file."""
    if not os.path.exists(path):
        print(f"Error: {label} '{path}' does not exist.")
        sys.exit(1)
    if not os.path.isfile(path):
        print(f"Error: {label} '{path}' is not a regular file.")
        sys.exit(1)
    if not os.access(path, os.R_OK):
        print(f"Error: {label} '{path}' is not readable.")
        sys.exit(1)


def _generate_srt(args):
    _ensure_readable_file(args.input)
    audio_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
            audio_path = audio_file.name

        print("Starting audio extraction...")
        ffmpeg_utils.extract_audio(args.input, audio_out=audio_path)
        print("Audio extracted successfully.")

        print("Starting transcription...")
        transcript = transcribe.transcribe_audio(audio_path, model_name="base")
        print()
        if transcript.strip():
            print(transcript)
        print()
        print("Transcription completed.")
    except (FileNotFoundError, RuntimeError) as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if audio_path:
            try:
                os.remove(audio_path)
            except FileNotFoundError:
                pass
            except OSError as e:
                print(f"Warning: Unable to remove temporary audio file: {e}")


def main():
    display_startup_banner()

    parser = argparse.ArgumentParser(
        prog="subify",
        description="Subify-CLI — generate transcripts from video files.",
    )
    parser.add_argument("--version", action="version", version="0.1.0")

    subparsers = parser.add_subparsers(dest="command")

    p_gen = subparsers.add_parser("generate-srt", help="Generate transcript from video")
    p_gen.add_argument("input", help="Input video file")
    p_gen.set_defaults(func=_generate_srt)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

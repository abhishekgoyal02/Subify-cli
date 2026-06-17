import argparse
import os
import sys
import tempfile

from .banner import (
    display_startup_banner,
    record_pipeline_output,
    stop_pipeline,
    update_pipeline,
)
from . import ffmpeg_utils, transcribe, srt_writer, embed


def _pipeline_print(*values, sep: str = " ", end: str = "\n") -> None:
    print(*values, sep=sep, end=end, flush=True)
    if sys.stdout.isatty():
        record_pipeline_output(sep.join(str(value) for value in values) + end)


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
    update_pipeline(stage=1)
    audio_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
            audio_path = audio_file.name

        _pipeline_print("Starting audio extraction...")
        ffmpeg_utils.extract_audio(args.input, audio_out=audio_path)
        _pipeline_print("Audio extracted successfully.")
        update_pipeline(stage=2)

        _pipeline_print("Starting transcription...")
        result = transcribe.transcribe_audio_with_segments(audio_path, model_name="base")
        update_pipeline(stage=3)
        _pipeline_print()
        transcript = result.text
        if transcript.strip():
            _pipeline_print(transcript)
        _pipeline_print()
        _pipeline_print("Transcription completed.")

        srt_content = srt_writer.generate_srt(result.segments)
        if not srt_content.strip():
            _pipeline_print("Error: Transcription result is empty.")
            sys.exit(1)

        input_path = args.input
        base, _ = os.path.splitext(input_path)
        srt_path = base + ".srt"

        try:
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
        except PermissionError:
            _pipeline_print(f"Error: Permission denied. Unable to write to '{srt_path}'.")
            sys.exit(1)
        except OSError as e:
            _pipeline_print(f"Error: Failed to write SRT file: {e}")
            sys.exit(1)

        _pipeline_print(f"SRT saved successfully: {srt_path}")
    except (FileNotFoundError, RuntimeError) as e:
        _pipeline_print(f"Error: {e}")
        sys.exit(1)
    finally:
        if audio_path:
            try:
                os.remove(audio_path)
            except FileNotFoundError:
                pass
            except OSError as e:
                _pipeline_print(f"Warning: Unable to remove temporary audio file: {e}")


def _process_video(args):
    _ensure_readable_file(args.input)
    update_pipeline(stage=1)
    audio_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
            audio_path = audio_file.name

        _pipeline_print("Starting audio extraction...")
        ffmpeg_utils.extract_audio(args.input, audio_out=audio_path)
        _pipeline_print("Audio extracted successfully.")
        update_pipeline(stage=2)

        _pipeline_print("Starting transcription...")
        result = transcribe.transcribe_audio_with_segments(audio_path, model_name="base")
        update_pipeline(stage=3)
        _pipeline_print()
        transcript = result.text
        if transcript.strip():
            _pipeline_print(transcript)
        _pipeline_print()
        _pipeline_print("Transcription completed.")

        _pipeline_print("Generating subtitles...")
        srt_content = srt_writer.generate_srt(result.segments)
        if not srt_content.strip():
            _pipeline_print("Error: Transcription result is empty.")
            sys.exit(1)

        input_path = args.input
        base, _ = os.path.splitext(input_path)
        srt_path = base + ".srt"

        try:
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
        except PermissionError:
            _pipeline_print(f"Error: Permission denied. Unable to write to '{srt_path}'.")
            sys.exit(1)
        except OSError as e:
            _pipeline_print(f"Error: Failed to write SRT file: {e}")
            sys.exit(1)

        _pipeline_print("Subtitles generated successfully.")

        _pipeline_print("Embedding subtitles...")
        output_path = base + "_subtitled.mp4"
        try:
            embed.embed_subtitles(
                video_path=input_path,
                subtitle_path=srt_path,
                output_path=output_path
            )
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            _pipeline_print(f"Error: {e}")
            sys.exit(1)

        _pipeline_print("Subtitled video generated successfully.")
        _pipeline_print(f"Output: {output_path}")
        update_pipeline(stage=4)

    except (FileNotFoundError, RuntimeError) as e:
        _pipeline_print(f"Error: {e}")
        sys.exit(1)
    finally:
        if audio_path:
            try:
                os.remove(audio_path)
            except FileNotFoundError:
                pass
            except OSError as e:
                _pipeline_print(f"Warning: Unable to remove temporary audio file: {e}")


def main():
    display_startup_banner()

    try:
        parser = argparse.ArgumentParser(
            prog="subify",
            description="Subify-CLI — generate transcripts from video files.",
        )
        parser.add_argument("--version", action="version", version="0.1.0")

        subparsers = parser.add_subparsers(dest="command")

        p_gen = subparsers.add_parser("generate-srt", help="Generate transcript from video")
        p_gen.add_argument("input", help="Input video file")
        p_gen.set_defaults(func=_generate_srt)

        p_proc = subparsers.add_parser("process", help="Process video to extract, transcribe, generate SRT, and embed subtitles")
        p_proc.add_argument("input", help="Input video file")
        p_proc.set_defaults(func=_process_video)

        args = parser.parse_args()
        if hasattr(args, "func"):
            args.func(args)
        else:
            parser.print_help()
    finally:
        stop_pipeline()


if __name__ == "__main__":
    main()

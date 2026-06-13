"""Transcription helpers.

This module will (for now) only handle extracting audio by delegating to
ffmpeg_utils. Later it will call ASR models to generate SRT files.
"""
from . import ffmpeg_utils


def transcribe(video_path: str, audio_out: str = "audio.wav") -> str:
    """Extract audio from the given video and return the audio path.

    Args:
        video_path: Path to the input video file.
        audio_out: Desired output audio filename.

    Returns:
        Path to the extracted audio file.

    Raises:
        FileNotFoundError: if ffmpeg is not installed.
        RuntimeError: if ffmpeg fails to extract audio.
    """
    # Start extraction using ffmpeg helper — allow exceptions to bubble up for the CLI to report
    ffmpeg_utils.extract_audio(video_path, audio_out)
    return audio_out

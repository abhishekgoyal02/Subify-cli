"""Audio extraction helper."""
from . import ffmpeg_utils


def transcribe(video_path: str, audio_out: str = "audio.wav") -> str:
    """Extract audio from the given video and return the audio path."""
    ffmpeg_utils.extract_audio(video_path, audio_out)
    return audio_out

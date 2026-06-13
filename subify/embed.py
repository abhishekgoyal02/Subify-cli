"""Embed module (future): burn subtitles into a video.

This module exists to keep the pipeline surface visible. It intentionally
contains no runtime side effects and no placeholder prints. Implementations
should call ffmpeg_utils to perform the actual work.
"""
from typing import Optional


def embed_subtitles(video_path: str, srt_path: str, output_path: Optional[str] = None) -> str:
    """Embed subtitles into `video_path` and return the output path.

    This function is a stub to make the future responsibility explicit. Using
    NotImplementedError prevents accidental use while keeping the API visible.
    """
    raise NotImplementedError(
        "embed_subtitles is not implemented yet. Implement using ffmpeg_utils.burn_subtitles." 
    )

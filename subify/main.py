"""Pipeline orchestrator (future).

This module is the intended place for the end-to-end pipeline orchestration
(e.g., extract audio, transcribe, generate subtitles, optionally burn
subtitles). It is intentionally a minimal stub to make the future pipeline
boundary explicit while preventing accidental use.
"""
from typing import Optional


def run_pipeline(input_video: str, burn: bool = True, output_path: Optional[str] = None) -> str:
    """Run the full pipeline and return the primary output path.

    This function is a stub. Replace with a concrete implementation that
    composes transcribe, ASR, subtitle generation, and optional burning.
    """
    raise NotImplementedError("run_pipeline is not implemented. Use subify.cli for current CLI behaviour.")

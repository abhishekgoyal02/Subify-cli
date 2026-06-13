"""Subify package initializer.

Exports include the CLI entrypoints and visible future modules to keep the
package surface explicit for later pipeline work.
"""

__all__ = ["cli", "transcribe", "ffmpeg_utils", "embed", "main"]
__version__ = "0.1.0"

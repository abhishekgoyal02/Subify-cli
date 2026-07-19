"""Project-specific operational errors."""


class SubifyError(Exception):
    """Base class for expected Subify failures."""


class InputValidationError(SubifyError):
    """Raised when the input video path cannot be processed."""


class DependencyError(SubifyError):
    """Raised when an external dependency is unavailable."""


class FFmpegError(SubifyError):
    """Raised when an FFmpeg command fails."""


class TranscriptionError(SubifyError):
    """Raised when speech-to-text processing fails."""


class SRTError(SubifyError):
    """Raised when SRT subtitle generation fails."""


class EmbeddingError(SubifyError):
    """Raised when subtitles cannot be embedded into the video."""


class PackagingError(SubifyError):
    """Raised when final result packaging fails."""

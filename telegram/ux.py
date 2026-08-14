"""Centralized Telegram user-facing copy for Subify."""

from __future__ import annotations

from subify.errors import (
    DependencyError,
    EmbeddingError,
    FFmpegError,
    InputValidationError,
    PackagingError,
    SRTError,
    SubifyError,
    TranscriptionError,
)

from .errors import TelegramApiError

INITIAL_STATUS_MESSAGE = "aight, let me see what we're working with 🫡"
SUCCESS_STATUS_MESSAGE = "yeah, we cooked. 🫡"
ZIP_CAPTION = "your zip has entered the chat 📦"

NO_VIDEO_MESSAGE = "send me an .mp4 and i'll make it readable."
UNSUPPORTED_FILE_MESSAGE = "nah, subify only speaks .mp4 right now."

TELEGRAM_STAGE_MESSAGES = {
    "input_validation": "checking if this video is gonna behave 🧐",
    "dependency_validation": "checking if this video is gonna behave 🧐",
    "duration_validation": "checking if this video is gonna behave 🧐",
    "disk_space_validation": "checking if this video is gonna behave 🧐",
    "audio_extraction": "stealing the audio real quick 🎧",
    "english_transcription": "time to make the AI actually listen 🧠",
    "srt_generation": "turning all that yapping into timestamps ⏱️",
    "subtitle_embedding": "making those subtitles stick to the frames 🔥",
    "zip_packaging": "zip file is getting its little suitcase packed 📦",
}


def stage_message(stage: str) -> str:
    return TELEGRAM_STAGE_MESSAGES.get(stage, "subify is handling the next bit.")


def pipeline_error_message(exc: SubifyError) -> str:
    if isinstance(exc, InputValidationError):
        message = str(exc)
        if "12 minutes" in message:
            return "12 minutes is the ceiling. this one crossed it."
        if "Only .mp4" in message:
            return UNSUPPORTED_FILE_MESSAGE
        if "Not enough" in message:
            return "storage is fighting for its life. free up some space and try again."
        return "yeah... this video is kinda cursed. i can't read it."
    if isinstance(exc, DependencyError):
        return "toolbox check failed. a required dependency is missing."
    if isinstance(exc, FFmpegError):
        return "couldn't get the media to behave. ffmpeg is being dramatic."
    if isinstance(exc, TranscriptionError):
        return "whisper got lost somewhere in the audio."
    if isinstance(exc, SRTError):
        return "the transcript exists, but the subtitles refused to materialize."
    if isinstance(exc, EmbeddingError):
        return "the words refused to stick to the video."
    if isinstance(exc, PackagingError):
        return "we cooked everything except the zip. tragic."
    return "subify hit a weird known failure. try again."


def telegram_upload_error_message(exc: TelegramApiError) -> str:
    description = exc.description.strip()
    lowered = description.lower()
    if "file is too big" in lowered or "too large" in lowered:
        return "telegram said absolutely not — this file is too large."
    if description:
        return f"we cooked the video, but telegram fumbled the handoff: {description}"
    return "we cooked the video, but telegram fumbled the handoff."


def unknown_error_message() -> str:
    return "something went sideways on our end. try again."

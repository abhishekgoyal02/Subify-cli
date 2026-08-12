"""Telegram update handlers that adapt user videos to the Subify pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Protocol

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
from subify import pipeline as subify_pipeline
from subify.pipeline import ProgressEvent

LOGGER = logging.getLogger(__name__)

SUPPORTED_VIDEO_SUFFIX = ".mp4"
STAGE_LABELS = {
    "input_validation": "Validating video",
    "dependency_validation": "Checking processing tools",
    "duration_validation": "Checking video length",
    "disk_space_validation": "Checking available space",
    "audio_extraction": "Extracting audio",
    "english_transcription": "Generating transcript",
    "srt_generation": "Writing subtitles",
    "subtitle_embedding": "Embedding subtitles",
    "zip_packaging": "Packaging result",
}


class TelegramClient(Protocol):
    def send_message(self, chat_id: int, text: str) -> dict[str, Any]:
        ...

    def edit_message_text(self, chat_id: int, message_id: int, text: str) -> dict[str, Any]:
        ...

    def get_file(self, file_id: str) -> dict[str, Any]:
        ...

    def download_file(self, file_path: str, destination: Path) -> Path:
        ...

    def send_document(self, chat_id: int, document_path: Path, *, caption: str | None = None) -> dict[str, Any]:
        ...


class TelegramVideoHandler:
    def __init__(self, client: TelegramClient) -> None:
        self._client = client

    def handle_update(self, update: dict[str, Any]) -> None:
        message = _get_value(update, "message")
        if message is None:
            return

        chat = _get_value(message, "chat")
        chat_id = _get_value(chat, "id") if chat is not None else None
        if not isinstance(chat_id, int):
            return

        attachment = _extract_video_attachment(message)
        if attachment is None:
            self._client.send_message(chat_id, "Please send an .mp4 video file.")
            return

        file_id = attachment["file_id"]
        file_name = _safe_filename(attachment.get("file_name") or "telegram-video.mp4")
        if Path(file_name).suffix.lower() != SUPPORTED_VIDEO_SUFFIX:
            self._client.send_message(chat_id, "Only .mp4 videos are supported in this version.")
            return

        status = self._client.send_message(chat_id, "Video received. Processing...")
        status_message_id = _message_id(status)

        with TemporaryDirectory(prefix="subify-telegram-") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            input_path = temp_dir / "input" / file_name
            output_dir = temp_dir / "output"
            try:
                file_info = self._client.get_file(file_id)
                file_path = file_info.get("file_path")
                if not isinstance(file_path, str) or not file_path:
                    raise InputValidationError("Telegram did not provide a downloadable video file.")

                self._client.download_file(file_path, input_path)
                result = subify_pipeline.process_video(
                    input_path,
                    output_dir=output_dir,
                    progress_callback=self._progress_callback(chat_id, status_message_id),
                )
                if result.zip_path is None or not result.zip_path.exists():
                    raise PackagingError("Subify did not produce a ZIP file.")

                _send_or_edit(
                    self._client,
                    chat_id,
                    status_message_id,
                    "Processing complete.",
                )
                self._client.send_document(chat_id, result.zip_path, caption="Processing complete.")
            except SubifyError as exc:
                LOGGER.info("Telegram video processing failed: %s", exc)
                self._client.send_message(chat_id, f"Processing failed:\n{telegram_error_message(exc)}")
            except Exception:
                LOGGER.exception("Unexpected Telegram video processing failure")
                self._client.send_message(
                    chat_id,
                    "Processing failed:\nAn unexpected error occurred while processing this video.",
                )

    def _progress_callback(self, chat_id: int, status_message_id: int | None):
        def report(event: ProgressEvent) -> None:
            stage, status = event
            if status != "start":
                return
            label = STAGE_LABELS.get(stage, stage.replace("_", " ").title())
            _send_or_edit(self._client, chat_id, status_message_id, f"{label}...")

        return report


def telegram_error_message(exc: SubifyError) -> str:
    if isinstance(exc, InputValidationError):
        message = str(exc)
        if "12 minutes" in message:
            return "The maximum supported video length is 12 minutes."
        if "Only .mp4" in message:
            return "Only .mp4 videos are supported in this version."
        if "Not enough" in message:
            return "Subify does not have enough temporary disk space to process this video."
        return "This video could not be read. Please send a valid .mp4 file."
    if isinstance(exc, DependencyError):
        return "Subify cannot process this video because a required dependency is unavailable."
    if isinstance(exc, FFmpegError):
        return "This video could not be read or processed. Please send a valid .mp4 file."
    if isinstance(exc, TranscriptionError):
        return "Subify could not generate a transcript for this video."
    if isinstance(exc, SRTError):
        return "Subify could not generate the subtitle file."
    if isinstance(exc, EmbeddingError):
        return "Subify could not embed subtitles into this video."
    if isinstance(exc, PackagingError):
        return "Subify could not package the processed files."
    return "Subify could not process this video."


def _extract_video_attachment(message: dict[str, Any]) -> dict[str, str] | None:
    for key in ("video", "document"):
        value = _get_value(message, key)
        if value is None:
            continue
        file_id = _get_value(value, "file_id")
        if not isinstance(file_id, str) or not file_id:
            continue
        file_name = _get_value(value, "file_name")
        return {
            "file_id": file_id,
            "file_name": file_name if isinstance(file_name, str) else "telegram-video.mp4",
        }
    return None


def _safe_filename(file_name: str) -> str:
    normalized = file_name.replace("\\", "/")
    candidate = Path(normalized).name.strip()
    return candidate or "telegram-video.mp4"


def _message_id(message: dict[str, Any]) -> int | None:
    value = _get_value(message, "message_id")
    return value if isinstance(value, int) else None


def _get_value(source: Any, key: str) -> Any:
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)


def _send_or_edit(client: TelegramClient, chat_id: int, message_id: int | None, text: str) -> None:
    if message_id is None:
        client.send_message(chat_id, text)
        return
    try:
        client.edit_message_text(chat_id, message_id, text)
    except Exception:
        LOGGER.info("Unable to edit Telegram status message; sending a new message instead.", exc_info=True)
        client.send_message(chat_id, text)

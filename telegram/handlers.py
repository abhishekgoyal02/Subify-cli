"""Telegram update handlers that adapt user videos to the Subify pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any, Protocol

from .errors import TelegramApiError
from .ux import (
    INITIAL_STATUS_MESSAGE,
    NO_VIDEO_MESSAGE,
    SUCCESS_STATUS_MESSAGE,
    UNSUPPORTED_FILE_MESSAGE,
    ZIP_CAPTION,
    pipeline_error_message,
    stage_message,
    telegram_upload_error_message,
    unknown_error_message,
)
from subify import pipeline as subify_pipeline
from subify.errors import InputValidationError, PackagingError, SubifyError
from subify.pipeline import ProgressEvent
from subify.transcribe import WhisperTranscriber, recommended_cpu_threads

LOGGER = logging.getLogger(__name__)

SUPPORTED_VIDEO_SUFFIX = ".mp4"
STATUS_UPDATE_STAGES = frozenset(
    {
        "english_transcription",
        "subtitle_embedding",
        "zip_packaging",
    }
)


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
    def __init__(self, client: TelegramClient, transcriber: WhisperTranscriber | None = None) -> None:
        self._client = client
        self._transcriber = (
            transcriber
            if transcriber is not None
            else WhisperTranscriber(beam_size=1, cpu_threads=recommended_cpu_threads())
        )

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
            self._client.send_message(chat_id, NO_VIDEO_MESSAGE)
            return

        file_id = attachment["file_id"]
        file_name = _safe_filename(attachment.get("file_name") or "telegram-video.mp4")
        if Path(file_name).suffix.lower() != SUPPORTED_VIDEO_SUFFIX:
            self._client.send_message(chat_id, UNSUPPORTED_FILE_MESSAGE)
            return

        status = _StatusMessage(self._client, chat_id, INITIAL_STATUS_MESSAGE)

        with TemporaryDirectory(prefix="subify-telegram-") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            input_path = temp_dir / "input" / file_name
            output_dir = temp_dir / "output"
            try:
                download_started_at = perf_counter()
                file_info = self._client.get_file(file_id)
                file_path = file_info.get("file_path")
                if not isinstance(file_path, str) or not file_path:
                    raise InputValidationError("Telegram did not provide a downloadable video file.")

                self._client.download_file(file_path, input_path)
                LOGGER.info(
                    "Telegram video download finished: chat_id=%s elapsed=%.2fs size_bytes=%s",
                    chat_id,
                    perf_counter() - download_started_at,
                    _safe_file_size(input_path),
                )
                processing_started_at = perf_counter()
                result = subify_pipeline.process_video(
                    input_path,
                    output_dir=output_dir,
                    progress_callback=self._progress_callback(status),
                    transcription_function=self._transcriber.transcribe_audio,
                )
                LOGGER.info(
                    "Telegram Subify processing finished: chat_id=%s elapsed=%.2fs",
                    chat_id,
                    perf_counter() - processing_started_at,
                )
                if not _is_uploadable_zip(result.zip_path):
                    raise PackagingError("Subify did not produce a ZIP file.")

                LOGGER.info(
                    "Sending Subify ZIP to Telegram: chat_id=%s file_name=%s size_bytes=%s",
                    chat_id,
                    result.zip_path.name,
                    result.zip_path.stat().st_size,
                )
                status.edit(SUCCESS_STATUS_MESSAGE)
                upload_started_at = perf_counter()
                self._client.send_document(chat_id, result.zip_path, caption=ZIP_CAPTION)
                LOGGER.info(
                    "Telegram ZIP upload finished: chat_id=%s elapsed=%.2fs size_bytes=%s",
                    chat_id,
                    perf_counter() - upload_started_at,
                    result.zip_path.stat().st_size,
                )
            except TelegramApiError as exc:
                LOGGER.error("Telegram API %s failed while handling video: %s", exc.method, exc.description)
                status.edit(telegram_upload_error_message(exc))
            except SubifyError as exc:
                LOGGER.info("Telegram video processing failed: %s", exc)
                status.edit(pipeline_error_message(exc))
            except Exception:
                LOGGER.exception("Unexpected Telegram video processing failure")
                status.edit(unknown_error_message())

    def _progress_callback(self, status_message: "_StatusMessage"):
        def report(event: ProgressEvent) -> None:
            stage, status = event
            if status != "start":
                return
            if stage not in STATUS_UPDATE_STAGES:
                return
            status_message.edit(stage_message(stage))

        return report


telegram_error_message = pipeline_error_message


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


def _is_uploadable_zip(zip_path: Path | None) -> bool:
    if zip_path is None:
        return False
    try:
        return zip_path.is_file() and zip_path.stat().st_size > 0
    except OSError:
        return False


def _safe_file_size(path: Path) -> int | str:
    try:
        return path.stat().st_size
    except OSError:
        return "unknown"


def _get_value(source: Any, key: str) -> Any:
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)


class _StatusMessage:
    def __init__(self, client: TelegramClient, chat_id: int, initial_text: str) -> None:
        self._client = client
        self._chat_id = chat_id
        self._text = initial_text
        response = client.send_message(chat_id, initial_text)
        self._message_id = _message_id(response)

    @property
    def text(self) -> str:
        return self._text

    def edit(self, text: str) -> None:
        if text == self._text:
            return
        if self._message_id is None:
            self._text = text
            return
        try:
            self._client.edit_message_text(self._chat_id, self._message_id, text)
            self._text = text
        except Exception:
            LOGGER.info("Unable to edit Telegram status message; continuing without message spam.", exc_info=True)

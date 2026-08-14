"""Minimal Telegram Bot API runner for Subify."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any, BinaryIO
from urllib import error
from urllib import parse, request

from .errors import TelegramApiError, TelegramConfigError
from .handlers import TelegramVideoHandler

TOKEN_ENV_VAR = "SUBIFY_TELEGRAM_BOT_TOKEN"
DEFAULT_POLL_TIMEOUT_SECONDS = 30

LOGGER = logging.getLogger(__name__)


def load_bot_token(env: Mapping[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    token = source.get(TOKEN_ENV_VAR, "").strip()
    if not token:
        raise TelegramConfigError(f"{TOKEN_ENV_VAR} is required to run the Telegram bot.")
    return token


class BotApiClient:
    def __init__(self, token: str) -> None:
        self._api_base = f"https://api.telegram.org/bot{token}"
        self._file_base = f"https://api.telegram.org/file/bot{token}"

    def get_updates(self, *, offset: int | None = None, timeout: int = DEFAULT_POLL_TIMEOUT_SECONDS) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout, "allowed_updates": json.dumps(["message"])}
        if offset is not None:
            payload["offset"] = offset
        return list(self._api_request("getUpdates", payload))

    def send_message(self, chat_id: int, text: str) -> dict[str, Any]:
        return dict(self._api_request("sendMessage", {"chat_id": chat_id, "text": text}))

    def edit_message_text(self, chat_id: int, message_id: int, text: str) -> dict[str, Any]:
        return dict(
            self._api_request(
                "editMessageText",
                {"chat_id": chat_id, "message_id": message_id, "text": text},
            )
        )

    def get_file(self, file_id: str) -> dict[str, Any]:
        return dict(self._api_request("getFile", {"file_id": file_id}))

    def download_file(self, file_path: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with request.urlopen(f"{self._file_base}/{parse.quote(file_path)}") as response:
            destination.write_bytes(response.read())
        return destination

    def send_document(self, chat_id: int, document_path: Path, *, caption: str | None = None) -> dict[str, Any]:
        _validate_document_upload_path(document_path)
        fields: dict[str, str] = {"chat_id": str(chat_id)}
        if caption:
            fields["caption"] = caption
        LOGGER.info(
            "Uploading Telegram document via sendDocument: chat_id=%s file_name=%s size_bytes=%s",
            chat_id,
            document_path.name,
            document_path.stat().st_size,
        )
        return dict(self._multipart_request("sendDocument", fields, "document", document_path))

    def _api_request(self, method: str, payload: Mapping[str, Any]) -> Any:
        body = parse.urlencode(payload).encode("utf-8")
        req = request.Request(f"{self._api_base}/{method}", data=body)
        try:
            with request.urlopen(req) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise self._telegram_http_error(method, exc) from exc
        if not data.get("ok"):
            description = _telegram_description(data)
            LOGGER.error("Telegram API %s failed: %s", method, description)
            raise TelegramApiError(method, description)
        return data.get("result")

    def _multipart_request(
        self,
        method: str,
        fields: Mapping[str, str],
        file_field: str,
        file_path: Path,
    ) -> Any:
        boundary = f"subify-{uuid.uuid4().hex}"
        body = bytearray()
        for name, value in fields.items():
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
            body.extend(value.encode("utf-8"))
            body.extend(b"\r\n")

        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            (
                f'Content-Disposition: form-data; name="{file_field}"; '
                f'filename="{file_path.name}"\r\n'
                "Content-Type: application/zip\r\n\r\n"
            ).encode("utf-8")
        )
        with file_path.open("rb") as file:
            _append_binary_file(body, file)
        body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

        req = request.Request(
            f"{self._api_base}/{method}",
            data=bytes(body),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with request.urlopen(req) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise self._telegram_http_error(method, exc) from exc
        if not data.get("ok"):
            description = _telegram_description(data)
            LOGGER.error("Telegram API %s failed: %s", method, description)
            raise TelegramApiError(method, description)
        return data.get("result")

    def _telegram_http_error(self, method: str, exc: error.HTTPError) -> TelegramApiError:
        description = _http_error_description(exc)
        LOGGER.error("Telegram API %s failed with HTTP %s: %s", method, exc.code, description)
        return TelegramApiError(method, description, status_code=exc.code)


def _http_error_description(exc: error.HTTPError) -> str:
    try:
        raw_body = exc.read().decode("utf-8", errors="replace")
    except Exception:
        return exc.reason or "HTTP request failed"

    if not raw_body:
        return exc.reason or "HTTP request failed"

    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        return raw_body[:300]

    return _telegram_description(data)


def _telegram_description(data: Mapping[str, Any]) -> str:
    description = data.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()
    error_code = data.get("error_code")
    if isinstance(error_code, int):
        return f"Telegram returned error code {error_code}"
    return "Telegram API request failed"


def _validate_document_upload_path(document_path: Path) -> None:
    try:
        stat = document_path.stat()
    except OSError as exc:
        raise TelegramApiError("sendDocument", "Document file is not available for upload") from exc
    if not document_path.is_file():
        raise TelegramApiError("sendDocument", "Document upload path is not a regular file")
    if stat.st_size <= 0:
        raise TelegramApiError("sendDocument", "Document file is empty")


def _append_binary_file(body: bytearray, file: BinaryIO) -> None:
    while True:
        chunk = file.read(1024 * 1024)
        if not chunk:
            return
        body.extend(chunk)


def run_polling(client: BotApiClient, handler: TelegramVideoHandler | None = None) -> int:
    video_handler = handler if handler is not None else TelegramVideoHandler(client)
    offset: int | None = None
    while True:
        try:
            updates = client.get_updates(offset=offset)
        except TelegramApiError as exc:
            if exc.method == "getUpdates" and exc.status_code == 409:
                LOGGER.error(
                    "Telegram polling conflict: another getUpdates consumer is already running "
                    "for this bot token. Stop the other instance and restart this one."
                )
                return 1
            raise

        for update in updates:
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                offset = update_id + 1
            try:
                video_handler.handle_update(update)
            except Exception:
                LOGGER.exception("Unhandled Telegram update processing failure")
        time.sleep(0.1)


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    try:
        token = load_bot_token()
    except TelegramConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return run_polling(BotApiClient(token))


if __name__ == "__main__":
    raise SystemExit(main())

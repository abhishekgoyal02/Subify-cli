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
from typing import Any
from urllib import parse, request

from .handlers import TelegramVideoHandler

TOKEN_ENV_VAR = "SUBIFY_TELEGRAM_BOT_TOKEN"
DEFAULT_POLL_TIMEOUT_SECONDS = 30

LOGGER = logging.getLogger(__name__)


class TelegramConfigError(RuntimeError):
    """Raised when the Telegram adapter is not configured."""


class TelegramApiError(RuntimeError):
    """Raised when Telegram returns an unsuccessful response."""


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
        fields: dict[str, str] = {"chat_id": str(chat_id)}
        if caption:
            fields["caption"] = caption
        return dict(self._multipart_request("sendDocument", fields, "document", document_path))

    def _api_request(self, method: str, payload: Mapping[str, Any]) -> Any:
        body = parse.urlencode(payload).encode("utf-8")
        req = request.Request(f"{self._api_base}/{method}", data=body)
        with request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not data.get("ok"):
            raise TelegramApiError(f"Telegram API call failed: {method}")
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
        body.extend(file_path.read_bytes())
        body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

        req = request.Request(
            f"{self._api_base}/{method}",
            data=bytes(body),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not data.get("ok"):
            raise TelegramApiError(f"Telegram API call failed: {method}")
        return data.get("result")


def run_polling(client: BotApiClient, handler: TelegramVideoHandler | None = None) -> None:
    video_handler = handler if handler is not None else TelegramVideoHandler(client)
    offset: int | None = None
    while True:
        for update in client.get_updates(offset=offset):
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
    run_polling(BotApiClient(token))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

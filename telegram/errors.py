"""Telegram adapter errors."""

from __future__ import annotations


class TelegramConfigError(RuntimeError):
    """Raised when the Telegram adapter is not configured."""


class TelegramApiError(RuntimeError):
    """Raised when Telegram returns an unsuccessful response."""

    def __init__(self, method: str, description: str, *, status_code: int | None = None) -> None:
        self.method = method
        self.description = description
        self.status_code = status_code
        status = f"HTTP {status_code}: " if status_code is not None else ""
        super().__init__(f"Telegram API {method} failed: {status}{description}")


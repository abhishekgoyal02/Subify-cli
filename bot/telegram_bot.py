"""Telegram bot integration (future).

This module is present to keep the integration surface visible. It intentionally
contains no working bot logic. Implementers should raise NotImplementedError
or provide a proper integration behind feature flags when ready.
"""


def main():
    """Entry point for Telegram bot integration.

    This is a deliberate stub to avoid accidental execution. Implement the bot
    only when you intend to add runtime Telegram integration.
    """
    raise NotImplementedError("Telegram bot integration is not implemented in this repository milestone.")


if __name__ == "__main__":
    # Keep a safe, explicit failure mode when run directly
    main()

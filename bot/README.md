# Subify Telegram Bot

Telegram Phase 1 is implemented as a separate top-level `telegram` package.

The bot should call `subify.pipeline.process_video()` directly after downloading a user video. It must not duplicate FFmpeg handling, transcription, SRT generation, subtitle embedding, or ZIP packaging logic.

Start the bot with:

```powershell
$env:SUBIFY_TELEGRAM_BOT_TOKEN = "<token>"
python -m telegram
```

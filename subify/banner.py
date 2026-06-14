"""Startup identity and health summary for Subify-CLI."""
import importlib.util
from typing import Optional

from rich.align import Align
from rich.console import Console, Group
from rich.text import Text

from . import __version__, ffmpeg_utils

_SEPARATOR = "." * 52


def _build_artwork() -> Group:
    header_box = Group(
        Text("       ╭──────────────╮"),
        Text("       │  SUBIFY-CLI  │"),
        Text("       ╰──────────────╯"),
    )

    waveform = Group(
        Text("  ▄▄      ▄▄      ▄▄      ▄▄", style="dim"),
        Text(" ████    ████    ████    ████", style="dim"),
    )

    caption_block = Group(
        Text("  ───────────────────────", style="bright_black"),
        Text("  [ Generating Captions ]", style="bold"),
        Text("  ───────────────────────", style="bright_black"),
    )

    return Group(
        Align.center(header_box),
        "",
        Align.center(waveform),
        "",
        Align.center(caption_block),
    )


def _build_health_section() -> Group:
    ffmpeg_ready = bool(ffmpeg_utils.get_ffmpeg_path())
    whisper_ready = importlib.util.find_spec("faster_whisper") is not None

    ffmpeg_state = "✓ Ready" if ffmpeg_ready else "○ Not Available"
    whisper_state = "✓ Ready" if whisper_ready else "○ Not Installed"
    readiness = "System Ready." if ffmpeg_ready and whisper_ready else "Setup Required."

    return Group(
        Align.center(Text(f"FFmpeg  {ffmpeg_state}")),
        Align.center(Text(f"Whisper {whisper_state}")),
        Align.center(Text(readiness, style="bold")),
    )


def display_startup_banner(console: Optional[Console] = None) -> None:
    """Render the startup identity and system status block."""
    console = console or Console(stderr=True, highlight=False)
    console.print(Align.center(f"Welcome to SUBIFY-CLI v{__version__}", vertical="middle"), style="bold")
    console.print(Align.center(_SEPARATOR), style="bright_black")
    console.print()
    console.print(_build_artwork())
    console.print()
    console.print(Align.center(_SEPARATOR), style="bright_black")
    console.print()
    console.print(_build_health_section())
    console.print()

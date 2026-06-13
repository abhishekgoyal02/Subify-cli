"""Startup identity and health summary for Subify-CLI."""
from typing import Optional

from rich.align import Align
from rich.console import Console, Group
from rich.text import Text

from . import __version__, ffmpeg_utils

_DOT_LINE = "." * 52


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
    ffmpeg_state = "✓ Available" if ffmpeg_utils.get_ffmpeg_path() else "○ Not Available"
    status = Group(
        Align.center(Text(f"FFmpeg  {ffmpeg_state}")),
        Align.center(Text("Whisper ○ Not Installed")),
        Align.center(Text("Bot     ○ Disabled")),
    )
    return status


def display_startup_banner(console: Optional[Console] = None) -> None:
    """Render the startup identity and system status block."""
    console = console or Console(stderr=True, highlight=False)
    console.print(Align.center(f"Welcome to SUBIFY-CLI v{__version__}", vertical="middle"), style="bold")
    console.print(Align.center(_DOT_LINE), style="bright_black")
    console.print()
    console.print(_build_artwork())
    console.print()
    console.print(Align.center(_DOT_LINE), style="bright_black")
    console.print()
    console.print(_build_health_section())
    console.print()
    console.print("Ready.", style="bold")

"""Terminal UI components for Subify."""

from __future__ import annotations

import io
import sys
from pathlib import Path

ACCENT = "#E76F51"
WELCOME_INNER_PANEL_HEIGHT = 14

try:
    from rich import box
    from rich.align import Align
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:  # pragma: no cover - fallback path for minimal environments
    box = None
    Align = None
    Console = None
    Group = None
    Panel = None
    Table = None
    Text = None


def _make_console() -> "Console | None":
    """Create a Rich Console with forced UTF-8 on Windows to avoid encoding errors."""
    if Console is None:
        return None
    # On Windows the legacy console uses cp1252 which can't handle box-drawing
    # characters. Wrap stdout with UTF-8 so Rich renders them correctly.
    if sys.platform == "win32":
        utf8_stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        return Console(file=utf8_stdout, force_terminal=True)
    return Console()


console = _make_console()


def render_welcome(version: str, cwd: Path | None = None) -> None:
    """Render the no-command Subify welcome dashboard."""
    if console is None or Panel is None or Table is None or Text is None or Align is None:
        _render_plain_welcome(version, cwd)
        return

    width = console.width

    if width >= 96:
        left = _identity_panel(version, cwd, height=WELCOME_INNER_PANEL_HEIGHT)
        right = _getting_started_panel(height=WELCOME_INNER_PANEL_HEIGHT)
        grid = Table.grid(expand=True)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        grid.add_row(left, right)
        content = grid
    else:
        left = _identity_panel(version, cwd)
        right = _getting_started_panel()
        content = Group(left, right) if Group is not None else Table.grid()

    console.print(
        Panel(
            content,
            title=_header(version),
            title_align="left",
            border_style=ACCENT,
            box=box.ROUNDED if box is not None else None,
            padding=(0, 2),
        )
    )

    # Tagline below the main panel
    tip = Text()
    tip.append("  AI-Powered Subtitles ", style=f"bold {ACCENT}")
    tip.append(" · ", style="gray50")
    tip.append("Process", style="gray50")
    tip.append(" · ", style="gray50")
    tip.append("Generate-srt", style="gray50")
    tip.append(" · ", style="gray50")
    tip.append("Embed", style="gray50")
    tip.append(" · ", style="gray50")
    tip.append("Package", style="gray50")
    console.print(tip)
    console.print()


def render_dependency_status(*, ffmpeg_ready: bool, whisper_ready: bool, include_whisper: bool) -> None:
    if console is not None and Table is not None:
        table = Table(show_header=False, box=None, pad_edge=False)
        table.add_column("Dependency", style="white")
        table.add_column("Status")
        table.add_row("FFmpeg", _status_text(ffmpeg_ready))
        if include_whisper:
            table.add_row("Faster-Whisper", _status_text(whisper_ready))
        console.print(table)
        return

    print(f"FFmpeg         {'Ready' if ffmpeg_ready else 'Missing'}")
    if include_whisper:
        print(f"Faster-Whisper {'Ready' if whisper_ready else 'Missing'}")


def render_shell_help() -> None:
    lines = [
        "Interactive shell commands:",
        "  process <video>",
        "  generate-srt <video>",
        "  embed <video> <srt>",
        "  /help",
        "  /version",
        "  /clear",
        "  /exit",
        "",
        "Type / to see shell commands.",
    ]
    print_message("\n".join(lines))


def render_shell_error(message: str) -> None:
    print_message(f"[red]{message}[/]")


def render_unknown_shell_command(command: str) -> None:
    render_shell_error(f"Unknown command: {command}\nType /help for available commands.")


def render_shell_exit() -> None:
    print_message("Leaving Subify shell.")


def render_shell_suggestions(commands: tuple[str, ...]) -> None:
    print_message("  ".join(commands))


def clear_terminal() -> None:
    print("\033[2J\033[H", end="")


def render_stage(stage: str, status: str) -> None:
    if status == "start":
        print_message(f"[dim]  -[/] {stage}")
    elif status == "complete":
        print_message(f"[{ACCENT}]  OK[/] {stage}")


def render_transcript_header() -> None:
    print_message(f"[{ACCENT}]Transcript[/]")


def render_success(message: str, output_path: Path) -> None:
    print_message(f"\n[{ACCENT}]{message}[/]\n\nOutput:\n{output_path}")


def render_error(message: str) -> None:
    if console is not None:
        console.print(f"[red]Subify error:[/] {message}", stderr=True)
    else:
        print(f"Subify error: {message}", file=sys.stderr)


def print_message(message: str) -> None:
    if console is not None:
        console.print(message)
    else:
        print(message)


def _identity_panel(version: str, cwd: Path | None, height: int | None = None) -> Panel:
    body = Table.grid(expand=True)
    body.add_column(justify="center")
    body.add_row(Text("Welcome to Subify!", style=f"bold {ACCENT}"))
    body.add_row(Text(_headphones_icon(), style=f"bold {ACCENT}", justify="center"))
    body.add_row(Text(f"Subify-CLI v{version}", style=f"bold {ACCENT}", justify="center"))
    body.add_row(Text("AI-Powered English Subtitle Pipeline", style="white", justify="center"))
    if cwd is not None:
        body.add_row(Text(str(cwd), style="dim", justify="center", overflow="fold"))

    return Panel(
        Align.center(body),
        border_style=ACCENT,
        box=box.ROUNDED if box is not None else None,
        padding=(0, 2),
        height=height,
    )


def _getting_started_panel(height: int | None = None) -> Panel:
    help_instruction = Text("Run ", style="white")
    help_instruction.append("/help", style="dim")
    help_instruction.append(
        " to learn the Subify-CLI instructions and available shell actions.",
        style="white",
    )

    note = Text()
    note.append("Tip: ", style=f"bold {ACCENT}")
    note.append(
        "Start from the folder that contains your video files for the smoothest workflow.",
        style="dim",
    )

    body = Table.grid(expand=True)
    body.add_column()
    body.add_row(Text("Tips for getting started", style=f"bold {ACCENT}"))
    body.add_row(help_instruction)
    body.add_row(note)
    body.add_row(Text("─" * 52, style="dim"))
    body.add_row(Text("What's Subify?", style=f"bold {ACCENT}"))
    body.add_row(
        Text(
            "An end-to-end subtitle pipeline that transforms raw video into publish-ready content through a unified automated workflow behind a single powerful CLI.",
            style="white",
            overflow="fold",
        )
    )

    return Panel(
        body,
        border_style=ACCENT,
        box=box.ROUNDED if box is not None else None,
        padding=(0, 2),
        height=height,
    )


def _header(version: str) -> Text:
    text = Text()
    text.append(" Subify-CLI ", style=f"bold {ACCENT}")
    text.append(f"v{version}", style="dim")
    return text


def _headphones_icon() -> str:
    return "\n".join(
        [
            "  ╭───────╮   ",
            " ╭─╯       ╰─╮ ",
            " │   ●   ●   │ ",
            " │     ─     │ ",
            " ╰─╮   ▄   ╭─╯ ",
            "  │ █████ │   ",
            "  ╰───────╯   ",
        ]
    )


def _status_text(ready: bool) -> str:
    if ready:
        return f"[{ACCENT}]Ready[/]"
    return "[red]Missing[/]"


def _render_plain_welcome(version: str, cwd: Path | None) -> None:
    print("+------------------------------------------------------------+")
    print(f"| Subify-CLI v{version:<45}|")
    print("| Welcome to Subify!                                        |")
    print("| AI-Powered English Subtitle Pipeline                      |")
    print("|                                                            |")
    print("|   __====__                                                 |")
    print("|  /  o  o  \\                                                |")
    print("| |    __    |                                               |")
    print("|  \\__|__|__/                                                |")
    print("|                                                            |")
    print("| Tips for getting started                                   |")
    print("|   Run /help to learn Subify-CLI instructions and shell     |")
    print("|   actions. Start from your video folder for a smoother     |")
    print("|   workflow.                                                |")
    print("|   --------------------------------------------------------------     |")
    print("| What's Subify?                                             |")
    print("|   An end-to-end subtitle pipeline that transforms raw video into publish-ready content through a unified automated workflow behind a single powerful CLI.                                               |")
    if cwd is not None:
        print(f"| CWD: {str(cwd)[:53]:<53}|")
    print("+------------------------------------------------------------+")

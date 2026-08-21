"""Terminal UI components for Subify."""

from __future__ import annotations

import io
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

ACCENT = "#E76F51"
WELCOME_INNER_PANEL_HEIGHT = 14
SHELL_INPUT_PLACEHOLDER = "Ask Subify to do anything"
SHELL_DEFAULT_EXIT_HINT = "Press Ctrl+C to exit Subify, or type /exit."
SHELL_ARMED_EXIT_HINT = "Press Ctrl+C again to exit."
HELP_URL = "https://subify-cli.vercel.app/"

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
    if console is None or Panel is None or Table is None or Text is None:
        _render_plain_shell_help()
        return

    body = Table.grid()
    body.add_column()
    body.add_row(
        Text(
            "A quick map of the shell and what Subify actually does.",
            style="white",
            overflow="fold",
        )
    )
    body.add_row(Text("Type / to discover actions, then use arrows or Enter.", style="dim"))
    link = Text(HELP_URL, style="dim")
    body.add_row(link)

    console.print(
        Panel(
            body,
            title=Text(" SUBIFY HELP ", style=f"bold {ACCENT}"),
            title_align="left",
            border_style=ACCENT,
            box=box.ROUNDED if box is not None else None,
            padding=(1, 2),
            width=66,
        )
    )


def render_shell_error(message: str) -> None:
    print_message(f"[red]{message}[/]")


def render_unknown_shell_command(command: str) -> None:
    render_shell_error(f"Unknown command: {command}\nType /help for available commands.")


def render_shell_exit() -> None:
    print_message("Leaving Subify shell.")


def render_shell_suggestions(commands: tuple[str, ...]) -> None:
    if not commands:
        return
    if console is not None and Text is not None:
        for index, command in enumerate(commands):
            marker = "› " if index == 0 else "  "
            style = f"bold {ACCENT}" if index == 0 else "white"
            text = Text(marker, style=ACCENT if index == 0 else "dim")
            text.append(command, style=style)
            console.print(text)
        return
    print("\n".join(commands))


def render_shell_footer() -> None:
    print_message(f"[dim]{SHELL_DEFAULT_EXIT_HINT}[/]")


def render_shell_interrupt_hint() -> None:
    print_message(f"[dim]{SHELL_ARMED_EXIT_HINT}[/]")


def render_shell_history(history: Sequence[str]) -> None:
    entries = [entry for entry in history if entry.strip() != "/history"]
    if not entries:
        print_message("[dim]No shell history yet.[/]")
        return
    print_message("\n".join(entries[-20:]))


def read_shell_input(
    input_reader: Callable[[str], str] = input,
    *,
    suggestions: Sequence[str] = (),
    exit_hint: str = SHELL_DEFAULT_EXIT_HINT,
) -> str:
    """Read one command from the dedicated Subify shell input area."""
    if _can_read_native_shell_input(input_reader):
        return _read_native_shell_input(tuple(suggestions), exit_hint)

    top, prompt, bottom = _shell_input_frame()
    if top:
        _write_shell_input_line(top)
    try:
        return input_reader(prompt)
    finally:
        if bottom:
            _write_shell_input_line(bottom)


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
    body.add_row(Text("AI-Powered Subtitle Pipeline", style="white", justify="center"))
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


def _shell_input_frame() -> tuple[str, str, str]:
    if console is None:
        return "", f"{SHELL_INPUT_PLACEHOLDER} ", ""

    accent = _ansi_from_hex(ACCENT)
    dim = "\033[2m"
    reset = "\033[0m"
    top = f"{accent}╭─ Command{reset}"
    prompt = f"{_shell_input_prefix()}{dim}{SHELL_INPUT_PLACEHOLDER}{reset} "
    bottom = f"{accent}╰{'─' * 15}{reset}"
    return top, prompt, bottom


def _shell_input_prefix() -> str:
    return f"{_ansi_from_hex(ACCENT)}│\033[0m "


def _can_read_native_shell_input(input_reader: Callable[[str], str]) -> bool:
    return (
        input_reader is input
        and sys.platform == "win32"
        and console is not None
        and sys.stdin.isatty()
        and console.file.isatty()
    )


def _read_native_shell_input(suggestions: Sequence[str], exit_hint: str) -> str:
    import msvcrt

    top, _, bottom = _shell_input_frame()
    prompt = _shell_input_prefix()
    current_exit_hint = exit_hint
    output = console.file
    output.write(f"{top}\n")

    line: list[str] = []
    placeholder_visible = True
    highlighted = 0
    visible_suggestions: tuple[str, ...] = ()
    suggestions_closed = False
    _redraw_native_shell_input(
        output, prompt, line, placeholder_visible, suggestions, highlighted, bottom, current_exit_hint
    )
    while True:
        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):
            current_exit_hint = SHELL_DEFAULT_EXIT_HINT
            key = msvcrt.getwch()
            if key == "H":
                if visible_suggestions:
                    highlighted = (highlighted - 1) % len(visible_suggestions)
                    _redraw_native_shell_input(
                        output, prompt, line, placeholder_visible, suggestions, highlighted, bottom, current_exit_hint
                    )
                    visible_suggestions = _matching_suggestions("".join(line), suggestions)
                continue
            if key == "P":
                if visible_suggestions:
                    highlighted = (highlighted + 1) % len(visible_suggestions)
                    _redraw_native_shell_input(
                        output, prompt, line, placeholder_visible, suggestions, highlighted, bottom, current_exit_hint
                    )
                    visible_suggestions = _matching_suggestions("".join(line), suggestions)
                continue
            continue
        if key == "\x03":
            if current_exit_hint != SHELL_ARMED_EXIT_HINT:
                current_exit_hint = SHELL_ARMED_EXIT_HINT
                _redraw_native_shell_input(
                    output,
                    prompt,
                    line,
                    placeholder_visible,
                    suggestions,
                    highlighted,
                    bottom,
                    current_exit_hint,
                )
                visible_suggestions = _matching_suggestions("".join(line), suggestions)
                continue
            _finish_native_shell_input(output, prompt, line, placeholder_visible, bottom, current_exit_hint)
            output.flush()
            raise KeyboardInterrupt
        if key == "\x1a":
            _finish_native_shell_input(output, prompt, line, placeholder_visible, bottom, current_exit_hint)
            output.flush()
            raise EOFError
        if key in ("\r", "\n"):
            if visible_suggestions and line and "".join(line) != visible_suggestions[highlighted]:
                line = list(visible_suggestions[highlighted])
                _redraw_native_shell_input(
                    output, prompt, line, False, suggestions, highlighted, bottom, current_exit_hint
                )
            _finish_native_shell_input(output, prompt, line, False, bottom, current_exit_hint)
            output.flush()
            return "".join(line)
        if key == "\t":
            current_exit_hint = SHELL_DEFAULT_EXIT_HINT
            if visible_suggestions:
                line = list(visible_suggestions[highlighted])
                placeholder_visible = False
                highlighted = 0
                _redraw_native_shell_input(
                    output, prompt, line, placeholder_visible, suggestions, highlighted, bottom, current_exit_hint
                )
                visible_suggestions = _matching_suggestions("".join(line), suggestions)
            continue
        if key == "\x1b":
            current_exit_hint = SHELL_DEFAULT_EXIT_HINT
            visible_suggestions = ()
            highlighted = 0
            suggestions_closed = True
            _redraw_native_shell_input(
                output, prompt, line, placeholder_visible, (), highlighted, bottom, current_exit_hint
            )
            continue
        if key in ("\b", "\x7f"):
            current_exit_hint = SHELL_DEFAULT_EXIT_HINT
            if line:
                line.pop()
                highlighted = 0
                placeholder_visible = len(line) == 0
                suggestions_closed = False
                _redraw_native_shell_input(
                    output, prompt, line, placeholder_visible, suggestions, highlighted, bottom, current_exit_hint
                )
                visible_suggestions = _matching_suggestions("".join(line), suggestions)
            continue
        if not key.isprintable():
            continue

        current_exit_hint = SHELL_DEFAULT_EXIT_HINT
        line.append(key)
        placeholder_visible = False
        highlighted = 0
        suggestions_closed = False
        _redraw_native_shell_input(
            output, prompt, line, placeholder_visible, suggestions, highlighted, bottom, current_exit_hint
        )
        visible_suggestions = () if suggestions_closed else _matching_suggestions("".join(line), suggestions)


def _redraw_native_shell_input(
    output: io.TextIOBase,
    prompt: str,
    line: Sequence[str],
    placeholder_visible: bool,
    suggestions: Sequence[str],
    highlighted: int,
    bottom: str,
    exit_hint: str,
    show_hint: bool = True,
) -> None:
    value = "".join(line)
    visible_suggestions = _matching_suggestions(value, suggestions)
    output.write("\r\033[J")
    if placeholder_visible:
        output.write(f"{prompt}\033[2m{SHELL_INPUT_PLACEHOLDER}\033[0m")
        input_columns = 2
    else:
        output.write(f"{prompt}{value}")
        input_columns = 2 + len(value)

    if visible_suggestions:
        for index, suggestion in enumerate(visible_suggestions):
            if index == highlighted:
                output.write(f"\n{_ansi_from_hex(ACCENT)}› {suggestion}\033[0m")
            else:
                output.write(f"\n\033[37m  {suggestion}\033[0m")

    output.write(f"\n{bottom}")
    if show_hint:
        output.write(f"\n\033[2m{exit_hint}\033[0m")

    lines_below_input = len(visible_suggestions) + 1
    if show_hint:
        lines_below_input += 1
    output.write(f"\033[{lines_below_input}A")
    output.write("\r")
    if input_columns:
        output.write(f"\033[{input_columns}C")
    output.flush()


def _finish_native_shell_input(
    output: io.TextIOBase,
    prompt: str,
    line: Sequence[str],
    placeholder_visible: bool,
    bottom: str,
    exit_hint: str,
) -> None:
    _redraw_native_shell_input(
        output, prompt, line, placeholder_visible, (), 0, bottom, exit_hint, show_hint=False
    )
    output.write("\033[1B\r\n")


def _matching_suggestions(value: str, suggestions: Sequence[str]) -> tuple[str, ...]:
    if not value.startswith("/"):
        return ()
    return tuple(suggestion for suggestion in suggestions if suggestion.startswith(value))


def _render_plain_shell_help() -> None:
    print(
        "\n".join(
            [
                "SUBIFY HELP",
                "A quick map of the shell and what Subify actually does.",
                "Type / to discover actions, then use arrows or Enter.",
                HELP_URL,
            ]
        )
    )


def _write_shell_input_line(line: str) -> None:
    output = console.file if console is not None else sys.stdout
    output.write(f"{line}\n")
    output.flush()


def _ansi_from_hex(value: str) -> str:
    red = int(value[1:3], 16)
    green = int(value[3:5], 16)
    blue = int(value[5:7], 16)
    return f"\033[38;2;{red};{green};{blue}m"


def _render_plain_welcome(version: str, cwd: Path | None) -> None:
    print("+------------------------------------------------------------+")
    print(f"| Subify-CLI v{version:<45}|")
    print("| Welcome to Subify!                                        |")
    print("| AI-Powered Subtitle Pipeline                      |")
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

"""Interactive shell for Subify command routing."""

from __future__ import annotations

import shlex
from collections.abc import Callable, Sequence
from pathlib import Path

from . import __version__
from . import ui

PROMPT = "subify > "
DIRECT_COMMANDS = {"process", "generate-srt", "embed"}
SLASH_COMMANDS = ("/help", "/version", "/clear", "/exit")

CommandDispatcher = Callable[[Sequence[str]], int]
InputReader = Callable[[str], str]


def start_shell(dispatcher: CommandDispatcher, input_reader: InputReader = input) -> int:
    ui.render_welcome(__version__, Path.cwd())
    while True:
        try:
            line = input_reader(PROMPT)
        except EOFError:
            ui.render_shell_exit()
            return 0
        except KeyboardInterrupt:
            ui.print_message("")
            ui.render_shell_exit()
            return 0

        if not execute_shell_line(line, dispatcher):
            return 0


def execute_shell_line(line: str, dispatcher: CommandDispatcher) -> bool:
    stripped = line.strip()
    if not stripped:
        return True

    try:
        args = parse_shell_command(stripped)
    except ValueError as exc:
        ui.render_shell_error(str(exc))
        return True

    command = args[0].lower()
    if command == "/":
        ui.render_shell_suggestions(SLASH_COMMANDS)
        return True
    if command == "/help":
        ui.render_shell_help()
        return True
    if command == "/version":
        ui.print_message(f"Subify-CLI {__version__}")
        return True
    if command == "/clear":
        ui.clear_terminal()
        return True
    if command == "/exit":
        ui.render_shell_exit()
        return False
    if command in DIRECT_COMMANDS:
        _run_direct_command(args, dispatcher)
        return True

    ui.render_unknown_shell_command(args[0])
    return True


def parse_shell_command(line: str) -> list[str]:
    lexer = shlex.shlex(line, posix=False)
    lexer.whitespace_split = True
    lexer.commenters = ""
    return [_strip_outer_quotes(token) for token in lexer]


def command_usage(command: str) -> str:
    return {
        "process": "process <video>",
        "generate-srt": "generate-srt <video>",
        "embed": "embed <video> <srt>",
    }.get(command, command)


def _run_direct_command(args: Sequence[str], dispatcher: CommandDispatcher) -> None:
    if not _has_required_arguments(args):
        ui.render_shell_error(f"Usage: {command_usage(args[0])}")
        return

    try:
        dispatcher(args)
    except SystemExit as exc:
        if exc.code not in (None, 0):
            ui.render_shell_error("Invalid arguments. Type /help for available commands.")


def _has_required_arguments(args: Sequence[str]) -> bool:
    command = args[0].lower()
    required_lengths = {
        "process": 2,
        "generate-srt": 2,
        "embed": 3,
    }
    return len(args) >= required_lengths[command]


def _strip_outer_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value

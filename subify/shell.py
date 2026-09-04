"""Interactive shell for Subify command routing."""

from __future__ import annotations

import shlex
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from . import ui

CommandDispatcher = Callable[[Sequence[str]], int]
InputReader = Callable[[str], str]


@dataclass
class ShellContext:
    dispatcher: CommandDispatcher
    history: list[str]
    cwd: Path
    version: str


CommandHandler = Callable[[Sequence[str], ShellContext], bool]


def start_shell(dispatcher: CommandDispatcher, input_reader: InputReader = input) -> int:
    ui.clear_terminal()
    cwd = Path.cwd()
    ui.render_welcome(__version__, cwd)
    context = ShellContext(dispatcher=dispatcher, history=[], cwd=cwd, version=__version__)
    interrupt_armed = False
    while True:
        try:
            line = ui.read_shell_input(
                input_reader,
                suggestions=tuple(COMMANDS),
                exit_hint=(
                    ui.SHELL_ARMED_EXIT_HINT
                    if interrupt_armed
                    else ui.SHELL_DEFAULT_EXIT_HINT
                ),
            )
        except EOFError:
            ui.render_shell_exit()
            return 0
        except KeyboardInterrupt:
            if input_reader is input:
                ui.render_shell_exit()
                return 0
            if interrupt_armed:
                ui.render_shell_exit()
                return 0
            interrupt_armed = True
            continue

        interrupt_armed = False
        should_continue = execute_shell_line(line, dispatcher, context=context)
        stripped = line.strip()
        if stripped.startswith("/"):
            context.history.append(stripped)
        if not should_continue:
            return 0


def execute_shell_line(
    line: str,
    dispatcher: CommandDispatcher,
    *,
    history: Sequence[str] = (),
    context: ShellContext | None = None,
) -> bool:
    stripped = line.strip()
    if not stripped:
        return True

    if context is None:
        context = ShellContext(
            dispatcher=dispatcher,
            history=list(history),
            cwd=Path.cwd(),
            version=__version__,
        )

    if not stripped.startswith("/"):
        ui.render_legacy_shell_command_error()
        return True

    try:
        args = parse_shell_command(stripped)
    except ValueError as exc:
        ui.render_shell_error(str(exc))
        return True

    command = args[0].lower()
    if command == "/":
        ui.render_shell_suggestions(suggest_shell_commands(command))
        return True

    shell_command = COMMANDS.get(command)
    if shell_command is not None:
        return shell_command(args, context)

    ui.render_unknown_shell_command(args[0])
    return True


def parse_shell_command(line: str) -> list[str]:
    lexer = shlex.shlex(line, posix=False)
    lexer.whitespace_split = True
    lexer.commenters = ""
    return [_strip_outer_quotes(token) for token in lexer]


def suggest_shell_commands(prefix: str) -> tuple[str, ...]:
    if not prefix.startswith("/"):
        return ()
    return tuple(command for command in COMMANDS if command.startswith(prefix))


def command_usage(command: str) -> str:
    return {
        "/process": '/process "video.mp4"',
        "/generate-srt": '/generate-srt "video.mp4"',
        "/embed": '/embed "video.mp4" "video.srt"',
    }.get(command, command)


def _handle_help(_args: Sequence[str], _context: ShellContext) -> bool:
    ui.render_shell_help()
    return True


def _handle_version(_args: Sequence[str], context: ShellContext) -> bool:
    ui.print_message(f"Subify-CLI {context.version}")
    return True


def _handle_process(args: Sequence[str], context: ShellContext) -> bool:
    return _dispatch_existing_command(args, context, "process", min_args=2)


def _handle_generate_srt(args: Sequence[str], context: ShellContext) -> bool:
    return _dispatch_existing_command(args, context, "generate-srt", min_args=2)


def _handle_embed(args: Sequence[str], context: ShellContext) -> bool:
    return _dispatch_existing_command(args, context, "embed", min_args=3)


def _handle_config(_args: Sequence[str], context: ShellContext) -> bool:
    ui.render_shell_config(version=context.version, cwd=context.cwd)
    return True


def _handle_history(_args: Sequence[str], context: ShellContext) -> bool:
    ui.render_shell_history(context.history)
    return True


def _handle_clear(_args: Sequence[str], context: ShellContext) -> bool:
    ui.clear_terminal()
    ui.render_welcome(context.version, context.cwd)
    return True


def _handle_doctor(args: Sequence[str], context: ShellContext) -> bool:
    return _dispatch_existing_command(args, context, "doctor", min_args=1)


def _handle_exit(_args: Sequence[str], _context: ShellContext) -> bool:
    ui.render_shell_exit()
    return False


COMMANDS: dict[str, CommandHandler] = {
    "/help": _handle_help,
    "/version": _handle_version,
    "/process": _handle_process,
    "/generate-srt": _handle_generate_srt,
    "/embed": _handle_embed,
    "/config": _handle_config,
    "/history": _handle_history,
    "/clear": _handle_clear,
    "/doctor": _handle_doctor,
    "/exit": _handle_exit,
}


def _dispatch_existing_command(
    args: Sequence[str],
    context: ShellContext,
    command: str,
    *,
    min_args: int,
) -> bool:
    if len(args) < min_args:
        ui.render_shell_error(f"Usage: {command_usage(args[0])}")
        return True

    try:
        context.dispatcher([command, *args[1:]])
    except SystemExit as exc:
        if exc.code not in (None, 0):
            ui.render_shell_error("Invalid arguments. Type /help for available commands.")
    return True


def _strip_outer_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value

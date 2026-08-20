"""Lightweight diagnostics for ``subify doctor``."""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory

from . import __version__, ui
from .errors import SubifyError
from .ffmpeg_utils import find_ffmpeg, find_ffprobe
from .pipeline import (
    resolve_output_directory,
    validate_importable_dependency,
    validate_output_directory,
    validate_python_runtime,
)


class DoctorStatus(Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: DoctorStatus
    detail: str
    action: str | None = None


def doctor_command() -> int:
    _print_title()
    ui.print_message("")
    checks = _run_checks_with_activity()
    render_doctor(checks, include_title=False, animate_summary=True)
    return doctor_exit_code(checks)


def run_doctor_checks() -> list[DoctorCheck]:
    return [
        _check_python(),
        _check_ffmpeg(),
        _check_ffprobe(),
        _check_faster_whisper(),
        _check_output_directory(),
        _check_temporary_workspace(),
        _check_subify_cli(),
    ]


def doctor_exit_code(checks: list[DoctorCheck]) -> int:
    if any(check.status is DoctorStatus.FAIL for check in checks):
        return 1
    return 0


def render_doctor(
    checks: list[DoctorCheck],
    *,
    include_title: bool = True,
    animate_summary: bool = False,
) -> None:
    if include_title:
        _print_title()
        ui.print_message("")
    for check in checks:
        _print_check(check)
    ui.print_message("")
    if animate_summary:
        _pause_before_summary()

    passed = _count(checks, DoctorStatus.PASS)
    warnings = _count(checks, DoctorStatus.WARNING)
    failures = _count(checks, DoctorStatus.FAIL)

    _print_heading("Doctor Summary")
    if failures:
        ui.print_message("")
        _print_summary_line(DoctorStatus.FAIL, f"{passed}/{len(checks)} checks passed")
        ui.print_message("")
        ui.print_message("Issues Found:")
        for issue in _issues_found(checks):
            ui.print_message(f" • {issue}")
        commands = _recommended_commands(checks)
        if commands:
            ui.print_message("")
            ui.print_message("Run:")
            for command in commands:
                ui.print_message(command)
    else:
        ui.print_message("──────────────────────────")
        _print_checks_passed_line(passed, len(checks))
        if warnings:
            _print_summary_line(DoctorStatus.WARNING, f"{warnings} {_plural('warning', warnings)}")
        if warnings:
            ui.print_message("")
            ui.print_message("System usable with warnings.")
        else:
            ui.print_message("Status        : Ready to generate subtitles")


def _check_subify_cli() -> DoctorCheck:
    if __version__:
        return DoctorCheck("Subify-CLI", DoctorStatus.PASS, f"Version {__version__}")
    return DoctorCheck(
        "Subify-CLI",
        DoctorStatus.FAIL,
        "Version unavailable",
        "Reinstall Subify-CLI and try again.",
    )


def _check_python() -> DoctorCheck:
    version = f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    try:
        validate_python_runtime()
    except SubifyError:
        return DoctorCheck(
            "Python",
            DoctorStatus.FAIL,
            "Python version is unsupported",
            f"{version}. Install Python 3.11 or newer.",
        )
    return DoctorCheck("Python", DoctorStatus.PASS, f"{version} detected")


def _check_ffmpeg() -> DoctorCheck:
    try:
        find_ffmpeg()
    except SubifyError:
        return DoctorCheck(
            "FFmpeg",
            DoctorStatus.FAIL,
            "Not found",
            "Install FFmpeg and make it available on PATH.",
        )
    return DoctorCheck("FFmpeg", DoctorStatus.PASS, "ffmpeg.exe available in PATH")


def _check_ffprobe() -> DoctorCheck:
    try:
        find_ffprobe()
    except SubifyError:
        return DoctorCheck(
            "FFprobe",
            DoctorStatus.FAIL,
            "Not found",
            "Install FFmpeg and make FFprobe available on PATH.",
        )
    return DoctorCheck("FFprobe", DoctorStatus.PASS, "Media inspection tools ready")


def _check_faster_whisper() -> DoctorCheck:
    try:
        validate_importable_dependency(
            "faster_whisper",
            "faster-whisper is not installed. Install project dependencies first.",
        )
    except SubifyError:
        return DoctorCheck(
            "Faster-Whisper",
            DoctorStatus.FAIL,
            "Not installed",
            "Install project dependencies first.",
        )
    return DoctorCheck("Faster-Whisper", DoctorStatus.PASS, "Speech engine installed")


def _check_output_directory() -> DoctorCheck:
    try:
        validate_output_directory(resolve_output_directory(None))
    except SubifyError:
        return DoctorCheck(
            "Output Directory",
            DoctorStatus.FAIL,
            "Cannot write to the output location",
        )
    return DoctorCheck("Output Directory", DoctorStatus.PASS, "Write permissions verified")


def _check_temporary_workspace() -> DoctorCheck:
    try:
        with TemporaryDirectory(prefix="subify-doctor-") as temp_dir_name:
            marker = Path(temp_dir_name) / ".subify-temp-test"
            marker.write_text("", encoding="utf-8")
            marker.unlink()
    except OSError:
        return DoctorCheck(
            "Temp Workspace",
            DoctorStatus.FAIL,
            "Cannot create temporary files",
        )
    return DoctorCheck("Temp Workspace", DoctorStatus.PASS, "Temporary storage operational")


def _run_checks_with_activity() -> list[DoctorCheck]:
    if not _should_animate_activity():
        return run_doctor_checks()

    checks: list[DoctorCheck] = []
    errors: list[BaseException] = []

    def target() -> None:
        try:
            checks.extend(run_doctor_checks())
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()

    frames = (
        "Checking environment   ",
        "Checking environment.  ",
        "Checking environment.. ",
        "Checking environment...",
    )
    index = 0
    while thread.is_alive():
        _write_activity(frames[index % len(frames)])
        index += 1
        thread.join(0.12)

    _clear_activity()
    if errors:
        raise errors[0]
    return checks


def _pause_before_summary() -> None:
    if not _should_animate_activity():
        return

    frames = (
        "◐ Thinking through the results   ",
        "◓ Thinking through the results.  ",
        "◑ Thinking through the results.. ",
        "◒ Thinking through the results...",
    )
    started_at = time.monotonic()
    index = 0
    while time.monotonic() - started_at < 3.0:
        _write_activity(frames[index % len(frames)])
        index += 1
        time.sleep(0.12)
    _clear_activity()


def _should_animate_activity() -> bool:
    return sys.stdout.isatty()


def _write_activity(message: str) -> None:
    sys.stdout.write(f"\r{message}")
    sys.stdout.flush()


def _clear_activity() -> None:
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


def _print_title() -> None:
    if ui.console is not None and ui.Text is not None:
        text = ui.Text()
        text.append("Subify Doctor", style=f"bold {ui.ACCENT}")
        text.append(f" v{__version__}", style="dim")
        ui.console.print(text)
        return
    ui.print_message(f"Subify Doctor v{__version__}")


def _print_heading(label: str) -> None:
    if ui.console is not None and ui.Text is not None:
        text = ui.Text(label, style=f"bold {ui.ACCENT}")
        ui.console.print(text)
        return
    ui.print_message(label)


def _print_check(check: DoctorCheck) -> None:
    _print_diagnostic_line(check.status, check.name, check.detail)


def _print_summary_line(status: DoctorStatus, detail: str) -> None:
    if ui.console is not None and ui.Text is not None:
        ui.console.print(_diagnostic_text(status, detail, color_title=False))
        return
    ui.print_message(f"{_plain_indicator(status)} {detail}")


def _print_checks_passed_line(passed: int, total: int) -> None:
    if ui.console is not None and ui.Text is not None:
        text = ui.Text("Checks Passed : ")
        text.append("[")
        text.append("✓", style="green")
        text.append(f"] {passed}/{total}")
        ui.console.print(text)
        return
    ui.print_message(f"Checks Passed : [✓] {passed}/{total}")


def _print_diagnostic_line(status: DoctorStatus, name: str, detail: str) -> None:
    if ui.console is not None and ui.Text is not None:
        ui.console.print(_check_text(status, name, detail))
        return
    ui.print_message(f"{_plain_indicator(status)} {name:<17} {detail}")


def _diagnostic_text(status: DoctorStatus, value: str, *, color_title: bool) -> "ui.Text":
    text = ui.Text()
    text.append("[")
    text.append(_status_symbol(status), style=_status_style(status))
    text.append("] ")
    text.append(value, style=f"bold {ui.ACCENT}" if color_title else "")
    return text


def _check_text(status: DoctorStatus, name: str, detail: str) -> "ui.Text":
    text = _diagnostic_text(status, name, color_title=True)
    padding = max(1, 18 - len(name))
    text.append(" " * padding)
    text.append(detail)
    return text


def _plain_indicator(status: DoctorStatus) -> str:
    return f"[{_status_symbol(status)}]"


def _status_symbol(status: DoctorStatus) -> str:
    return {
        DoctorStatus.PASS: "✓",
        DoctorStatus.WARNING: "!",
        DoctorStatus.FAIL: "✗",
    }[status]


def _status_style(status: DoctorStatus) -> str:
    return {
        DoctorStatus.PASS: "green",
        DoctorStatus.WARNING: "yellow",
        DoctorStatus.FAIL: "red",
    }[status]


def _count(checks: list[DoctorCheck], status: DoctorStatus) -> int:
    return sum(1 for check in checks if check.status is status)


def _plural(word: str, count: int) -> str:
    if count == 1:
        return word
    return f"{word}s"


def _issues_found(checks: list[DoctorCheck]) -> list[str]:
    issues: list[str] = []
    for check in checks:
        if check.status is not DoctorStatus.FAIL:
            continue
        if check.name == "FFmpeg":
            issues.append("FFmpeg not found in PATH")
        elif check.name == "Faster-Whisper":
            issues.append("Faster-Whisper missing")
        elif check.name == "FFprobe":
            issues.append("FFprobe not found in PATH")
        else:
            issues.append(check.detail)
    return issues


def _recommended_commands(checks: list[DoctorCheck]) -> list[str]:
    if any(check.name == "Faster-Whisper" and check.status is DoctorStatus.FAIL for check in checks):
        return ["pip install faster-whisper"]
    return []

"""Startup identity and health summary for Subify-CLI."""
import importlib.util
import math
from typing import Optional

from rich.align import Align
from rich.cells import cell_len
from rich.console import Console, Group
from rich.control import Control
from rich.text import Text

from . import __version__, ffmpeg_utils

_SEPARATOR = "." * 52
_PIPELINE_STAGE_COUNT = 4
_PENDING_STAGE_STYLE = "dim"
_COMPLETED_STAGE_STYLE = "#CC7A29"
_LINES_AFTER_WAVEFORM_TOP = 13
_active_pipeline = None


def _build_pipeline_row(
    block: str, gap: str, leading_space: str, stage: int
) -> Text:
    row = Text(leading_space)
    for index in range(_PIPELINE_STAGE_COUNT):
        style = (
            _COMPLETED_STAGE_STYLE
            if index < stage
            else _PENDING_STAGE_STYLE
        )
        row.append(block, style=style)
        if index < _PIPELINE_STAGE_COUNT - 1:
            row.append(gap)
    return row


def _build_waveform(stage: int = 0) -> Group:
    if not 0 <= stage <= _PIPELINE_STAGE_COUNT:
        raise ValueError(
            f"Pipeline stage must be between 0 and {_PIPELINE_STAGE_COUNT}."
        )

    return Group(
        _build_pipeline_row("▄▄", "      ", "  ", stage),
        _build_pipeline_row("████", "    ", " ", stage),
    )


def _build_artwork(stage: int = 0) -> Group:
    header_box = Group(
        Text("       ╭──────────────╮"),
        Text("       │  SUBIFY-CLI  │"),
        Text("       ╰──────────────╯"),
    )

    waveform = _build_waveform(stage)

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


def _build_banner(stage: int = 0, health_section: Optional[Group] = None) -> Group:
    return Group(
        Align.center(
            Text(f"Welcome to SUBIFY-CLI v{__version__}", style="bold"),
            vertical="middle",
        ),
        Align.center(Text(_SEPARATOR, style="bright_black")),
        "",
        _build_artwork(stage),
        "",
        Align.center(Text(_SEPARATOR, style="bright_black")),
        "",
        health_section if health_section is not None else _build_health_section(),
        "",
    )


class PipelineDisplay:
    """Manage in-place updates to the startup banner milestone boxes."""

    def __init__(self, console: Optional[Console] = None, stage: int = 0) -> None:
        self.console = console or Console(stderr=True, highlight=False)
        self.stage = stage
        self._output_lines = 0
        self._health_section = _build_health_section()

    def start(self) -> None:
        self.console.print(_build_banner(self.stage, self._health_section))

    def update(self, stage: int) -> None:
        if not 0 <= stage <= _PIPELINE_STAGE_COUNT:
            raise ValueError(
                f"Pipeline stage must be between 0 and {_PIPELINE_STAGE_COUNT}."
            )
        self.stage = max(self.stage, stage)
        if not self.console.is_terminal:
            return

        lines_to_waveform = _LINES_AFTER_WAVEFORM_TOP + self._output_lines
        self.console.control(
            Control.move_to_column(0, y=-lines_to_waveform)
        )
        self.console.print(Align.center(_build_waveform(self.stage)))
        self.console.control(
            Control.move_to_column(0, y=lines_to_waveform - 2)
        )

    def record_output(self, text: str) -> None:
        """Track terminal rows printed beneath the banner."""
        if not text:
            return

        lines = text.split("\n")
        if text.endswith("\n"):
            lines.pop()

        width = max(1, self.console.width)
        self._output_lines += sum(
            max(1, math.ceil(cell_len(line) / width))
            for line in lines
        )

    def stop(self) -> None:
        pass


def display_startup_banner(
    console: Optional[Console] = None, stage: int = 0
) -> PipelineDisplay:
    """Render the startup identity and system status block."""
    global _active_pipeline
    if _active_pipeline is not None:
        _active_pipeline.stop()
    _active_pipeline = PipelineDisplay(console=console, stage=stage)
    _active_pipeline.start()
    return _active_pipeline


def update_pipeline(stage: int) -> None:
    """Update the milestone boxes in the active startup banner."""
    if _active_pipeline is None:
        raise RuntimeError("The startup banner is not active.")
    _active_pipeline.update(stage)


def record_pipeline_output(text: str) -> None:
    """Record output written below the active startup banner."""
    if _active_pipeline is not None:
        _active_pipeline.record_output(text)


def stop_pipeline() -> None:
    """Stop the active banner display and restore the terminal."""
    global _active_pipeline
    if _active_pipeline is not None:
        _active_pipeline.stop()
        _active_pipeline = None

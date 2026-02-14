"""Bottom status bar — session info, model, memory status."""

import time

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static
from textual.widget import Widget

from ora.config import OrAConfig


class StatusBar(Widget):
    """Single-line status bar with real info."""

    def __init__(self, config: OrAConfig, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config

    def compose(self) -> ComposeResult:
        with Horizontal(id="status-row"):
            yield Static("", id="status-model")
            yield Static("", id="status-memory")
            yield Static("", id="status-session")
            yield Static("", id="status-rate")

    def on_mount(self) -> None:
        self._update_status()
        self.set_interval(1.0, self._update_status)

    def _update_status(self) -> None:
        elapsed = time.time() - self.config.session_start
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)

        self.query_one("#status-model", Static).update(
            " [bold]MODEL[/] minimax-m2.1"
        )
        self.query_one("#status-memory", Static).update(
            " [bold]MEM[/] session"
        )
        self.query_one("#status-session", Static).update(
            f" [bold]UP[/] {minutes:02d}:{seconds:02d}"
        )
        self.query_one("#status-rate", Static).update(
            " [bold]RPM[/] 40"
        )

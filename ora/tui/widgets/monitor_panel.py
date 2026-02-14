"""System monitor panel — real psutil data."""

from textual.app import ComposeResult
from textual.widgets import Static, ProgressBar, Label, Sparkline
from textual.widget import Widget

from ora.config import OrAConfig
from ora.system_monitor import get_system_stats


class MonitorPanel(Widget):
    """Real-time system monitoring with CPU/RAM/Disk bars and CPU sparkline."""

    def __init__(self, config: OrAConfig, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config
        self._cpu_data: list[float] = []

    def compose(self) -> ComposeResult:
        yield Label("[bold]SYSTEM MONITOR[/]", id="monitor-title")
        yield Static("", id="cpu-stat")
        yield ProgressBar(total=100, show_eta=False, id="cpu-bar")
        yield Static("", id="ram-stat")
        yield ProgressBar(total=100, show_eta=False, id="ram-bar")
        yield Static("", id="disk-stat")
        yield ProgressBar(total=100, show_eta=False, id="disk-bar")
        yield Label("[dim]cpu history[/]", id="sparkline-label")
        yield Sparkline([], id="cpu-sparkline")

    def on_mount(self) -> None:
        self._refresh_stats()
        self.set_interval(self.config.refresh_interval, self._refresh_stats)

    def _refresh_stats(self) -> None:
        stats = get_system_stats()

        self.query_one("#cpu-stat", Static).update(
            f"  CPU  {stats.cpu_percent:5.1f}%  ({stats.cpu_count} cores)"
        )
        cpu_bar = self.query_one("#cpu-bar", ProgressBar)
        cpu_bar.progress = stats.cpu_percent

        self.query_one("#ram-stat", Static).update(
            f"  RAM  {stats.ram_used_gb}G / {stats.ram_total_gb}G  ({stats.ram_percent:.0f}%)"
        )
        ram_bar = self.query_one("#ram-bar", ProgressBar)
        ram_bar.progress = stats.ram_percent

        self.query_one("#disk-stat", Static).update(
            f"  DSK  {stats.disk_used_gb:.0f}G / {stats.disk_total_gb:.0f}G  ({stats.disk_percent:.1f}%)"
        )
        disk_bar = self.query_one("#disk-bar", ProgressBar)
        disk_bar.progress = stats.disk_percent

        self._cpu_data.append(stats.cpu_percent)
        if len(self._cpu_data) > 60:
            self._cpu_data = self._cpu_data[-60:]
        self.query_one("#cpu-sparkline", Sparkline).data = list(self._cpu_data)

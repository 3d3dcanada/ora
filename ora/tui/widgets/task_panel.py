"""Task queue panel — mock background tasks with progress."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static, Label
from textual.widget import Widget

from ora.task_manager import TaskManager, TaskStatus


STATUS_ICONS = {
    TaskStatus.RUNNING: "[bold green]▶[/]",
    TaskStatus.COMPLETED: "[bold green]✓[/]",
    TaskStatus.FAILED: "[bold red]✗[/]",
    TaskStatus.PAUSED: "[dim]⏸[/]",
    TaskStatus.PENDING: "[dim]…[/]",
}


class TaskPanel(Widget):
    """Displays background task queue with animated progress bars."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.task_manager = TaskManager()

    def compose(self) -> ComposeResult:
        yield Label("[bold]TASK QUEUE[/]", id="task-title")
        yield VerticalScroll(id="task-list")

    def on_mount(self) -> None:
        self._render_tasks()
        self.set_interval(1.0, self._tick_and_render)

    def _tick_and_render(self) -> None:
        self.task_manager.tick()
        self._render_tasks()

    def _render_tasks(self) -> None:
        container = self.query_one("#task-list", VerticalScroll)
        container.remove_children()

        for task in self.task_manager.tasks:
            icon = STATUS_ICONS.get(task.status, "?")
            pct = int(task.progress * 100)
            filled = int(task.progress * 20)
            empty = 20 - filled
            bar = f"[green]{'█' * filled}[/][dim]{'░' * empty}[/]"
            line = f"  {icon}  {bar} {pct:3d}%  {task.description}"
            container.mount(Static(line, markup=True))

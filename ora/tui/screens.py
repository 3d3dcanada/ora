"""Main screen with 4-pane layout + approval panel."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Vertical
from textual.widgets import Header

from tui.config import OrAConfig
from tui.widgets.chat_panel import ChatPanel
from tui.widgets.monitor_panel import MonitorPanel
from tui.widgets.task_panel import TaskPanel
from tui.widgets.status_bar import StatusBar
from tui.widgets.approval_panel import ApprovalPanel
from tui.orchestrator.service import OrchestratorService


class MainScreen(Screen):
    """Primary layout: Chat | Monitor + Tasks + Approval, with status bar."""

    def __init__(self, config: OrAConfig) -> None:
        super().__init__()
        self.config = config
        self.orchestrator = OrchestratorService()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            with Vertical(id="left-column"):
                yield ChatPanel(self.config, id="chat-panel")
            with Vertical(id="right-column"):
                yield MonitorPanel(self.config, id="monitor-panel")
                yield TaskPanel(id="task-panel")
                yield ApprovalPanel(id="approval-panel")
        yield StatusBar(self.config, id="status-bar")

    def on_mount(self) -> None:
        # Auto-focus chat input
        try:
            self.query_one("#chat-input").focus()
        except Exception:
            pass

    def on_approval_panel_approved(self, event: ApprovalPanel.Approved) -> None:
        result = self.orchestrator.approve(event.approval_id)
        chat = self.query_one("#chat-panel", ChatPanel)
        log = chat.query_one("#chat-log")
        if result.get("success"):
            log.write(f"\n[green]Approved: {result.get('operation', 'action')}[/]")
        else:
            log.write(f"\n[red]Approval failed: {result.get('error', 'unknown')}[/]")

    def on_approval_panel_rejected(self, event: ApprovalPanel.Rejected) -> None:
        result = self.orchestrator.reject(event.approval_id)
        chat = self.query_one("#chat-panel", ChatPanel)
        if hasattr(chat.backend, 'add_rejection') and result.get("success"):
            chat.backend.add_rejection(
                result.get("operation", "unknown"),
                "User rejected via approval panel"
            )
        log = chat.query_one("#chat-log")
        log.write(f"\n[yellow]Rejected: {result.get('operation', 'action')}[/]")

"""OrA — main Textual application."""

from textual.app import App, ComposeResult
from textual.binding import Binding

from tui.config import OrAConfig
from tui.screens import MainScreen


class OrAApp(App):
    """OrA — Autonomous AI Command Center."""

    TITLE = "OrA"
    SUB_TITLE = "Command Center"
    CSS_PATH = "css/ora.tcss"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+l", "focus_chat", "Chat"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.ora_config = OrAConfig()

    def on_mount(self) -> None:
        self.push_screen(MainScreen(self.ora_config))

    def action_focus_chat(self) -> None:
        try:
            self.query_one("#chat-input").focus()
        except Exception:
            pass

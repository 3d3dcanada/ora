"""Chat panel — main interaction with OrA."""

import asyncio
import re
from textual.app import ComposeResult
from textual.widgets import Input, RichLog
from textual.widget import Widget
from textual.message import Message

from ora.config import OrAConfig
from ora.persona import OrAPersona
from ora.backend.litellm_backend import LiteLLMBackend


_THINK_RE = re.compile(r'<think>.*?</think>\s*', flags=re.DOTALL)


class ChatPanel(Widget):
    """Chat display with message history and input."""

    class ResponseComplete(Message):
        pass

    def __init__(self, config: OrAConfig, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config
        self.persona = OrAPersona(user_name=config.user_name)
        self.backend = LiteLLMBackend(
            model="nvidia_nim/minimaxai/minimax-m2.1",
            user_name=config.user_name,
            enable_memory=True,
        )
        self._processing = False

    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-log", wrap=True, markup=True, max_lines=1000)
        yield Input(placeholder="Talk to OrA... (/help for commands)", id="chat-input")

    def on_mount(self) -> None:
        greeting = self.persona.greeting()
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[bold magenta]OrA[/] [dim]›[/] {greeting.text}")
        log.write("")

    def _handle_slash_command(self, cmd: str) -> bool:
        """Handle /commands. Returns True if handled."""
        log = self.query_one("#chat-log", RichLog)
        parts = cmd.strip().split(None, 1)
        command = parts[0].lower()

        if command in ("/help", "/?"):
            log.write("[bold cyan]Commands:[/]")
            log.write("  [cyan]/help[/]    — show this")
            log.write("  [cyan]/clear[/]   — clear chat")
            log.write("  [cyan]/model[/]   — show current model")
            log.write("  [cyan]/memory[/]  — show memory status")
            log.write("  [cyan]/status[/]  — system overview")
            log.write("  [cyan]/reset[/]   — clear conversation history")
            log.write("")
            return True

        if command == "/clear":
            log.clear()
            log.write("[dim]Chat cleared.[/]")
            log.write("")
            return True

        if command == "/model":
            log.write(f"[bold cyan]Model:[/] {self.backend.model}")
            mem = "available" if self.backend.memory_available else "offline"
            log.write(f"[bold cyan]Memory:[/] {mem}")
            log.write("")
            return True

        if command == "/memory":
            if self.backend.memory_available:
                log.write("[bold green]Memory:[/] Qdrant connected")
            else:
                log.write("[bold yellow]Memory:[/] Qdrant offline — session only")
            log.write("")
            return True

        if command == "/status":
            from ora.system_monitor import get_system_stats
            stats = get_system_stats()
            log.write(f"[bold cyan]CPU:[/]  {stats.cpu_percent:.0f}% ({stats.cpu_count} cores)")
            log.write(f"[bold cyan]RAM:[/]  {stats.ram_used_gb}G / {stats.ram_total_gb}G ({stats.ram_percent:.0f}%)")
            log.write(f"[bold cyan]Disk:[/] {stats.disk_used_gb:.0f}G / {stats.disk_total_gb:.0f}G ({stats.disk_percent:.0f}%)")
            log.write("")
            return True

        if command == "/reset":
            self.backend.clear_history()
            log.write("[dim]Conversation history cleared.[/]")
            log.write("")
            return True

        return False

    async def _stream_response(self, user_text: str) -> None:
        """Stream LLM response to chat log."""
        log = self.query_one("#chat-log", RichLog)

        try:
            full_response = ""
            async for chunk in self.backend.stream_message(user_text):
                full_response += chunk

            display = _THINK_RE.sub('', full_response).strip()

            if display:
                log.write(f"[bold magenta]OrA[/] [dim]›[/] {display}")
            else:
                log.write("[bold magenta]OrA[/] [dim]› (empty response)[/]")
            log.write("")

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)[:120]}"
            log.write(f"[bold red]Error[/] [dim]›[/] {error_msg}")
            response = self.persona.respond(user_text)
            log.write(f"[bold magenta]OrA[/] [dim](offline) ›[/] {response.text}")
            log.write("")

        self._processing = False
        self.post_message(self.ResponseComplete())

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        if not user_text or self._processing:
            return

        log = self.query_one("#chat-log", RichLog)
        input_widget = self.query_one("#chat-input", Input)
        input_widget.value = ""

        if user_text.startswith("/"):
            if self._handle_slash_command(user_text):
                return

        log.write(f"[bold cyan]You[/] [dim]›[/] {user_text}")
        self._processing = True
        asyncio.create_task(self._stream_response(user_text))

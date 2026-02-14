"""Chat backend protocol. Stub for Phase 2 (LiteLLM / LangGraph)."""

from typing import Protocol, AsyncIterator
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # "user" or "assistant"
    content: str
    timestamp: float


class ChatBackend(Protocol):
    """Protocol that Phase 2 backends must implement."""

    async def send_message(self, message: str) -> str: ...

    async def stream_message(self, message: str) -> AsyncIterator[str]: ...

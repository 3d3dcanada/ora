"""Backend implementations for OrA."""

from typing import Protocol, AsyncIterator
from dataclasses import dataclass


@dataclass
class ChatMessage:
    """A chat message with role and content."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float


class ChatBackend(Protocol):
    """Protocol that Phase 2 backends must implement."""

    async def send_message(self, message: str) -> str: ...

    async def stream_message(self, message: str) -> AsyncIterator[str]: ...


# Import here after defining ChatBackend to avoid circular import
from ora.backend.litellm_backend import LiteLLMBackend


__all__ = ["ChatBackend", "ChatMessage", "LiteLLMBackend"]

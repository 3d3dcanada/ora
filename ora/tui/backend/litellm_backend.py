"""LiteLLM-powered chat backend with NVIDIA NIM primary + fallbacks."""

import os
from pathlib import Path
from typing import AsyncIterator, Optional, Protocol
from dotenv import load_dotenv

import litellm
from litellm import acompletion

# Load environment variables from .env file (look in ora project root)
# __file__ is /home/randall/ora/src/ora/backend/litellm_backend.py
# We need to go up 4 levels to get to /home/randall/ora/
_ora_env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(_ora_env_path, override=True)


class ChatBackend(Protocol):
    """Protocol that backends must implement."""
    async def send_message(self, message: str) -> str: ...
    async def stream_message(self, message: str) -> AsyncIterator[str]: ...

# Suppress verbose LiteLLM logging
litellm.suppress_debug_info = True


class LiteLLMBackend(ChatBackend):
    """Real LLM backend using LiteLLM with NVIDIA NIM + fallbacks."""

    # System prompt defining OrA's personality
    SYSTEM_PROMPT_TEMPLATE = """You are OrA, an elite AI command center assistant.

Your personality:
- Street-smart and direct — no fluff, just results
- Elite execution mindset — you get things done
- "Do no harm" ethic — you warn about risky operations

{memory_context}

Be concise. Be helpful. Be real."""

    def __init__(
        self,
        model: str = "nvidia_nim/meta/llama-3.1-8b-instruct",
        user_name: str = "Randall",
        enable_memory: bool = True,
    ) -> None:
        self.model = model
        self.user_name = user_name
        self.conversation_history: list[dict] = []
        
        # Memory initialized lazily to avoid blocking on Qdrant connect
        self._memory = None
        self._memory_enabled = enable_memory
        self._memory_checked = False

        # Set API base for NVIDIA NIM if using their models
        if "nvidia" in model.lower():
            os.environ.setdefault(
                "NVIDIA_NIM_API_BASE",
                "https://integrate.api.nvidia.com/v1"
            )

    @property
    def memory(self):
        """Lazy memory init — won't block startup if Qdrant is down."""
        if not self._memory_enabled:
            return None
        if not self._memory_checked:
            self._memory_checked = True
            try:
                from ora.memory.pulz_memory import PulZMemory
                self._memory = PulZMemory(user_id=self.user_name.lower())
            except Exception:
                self._memory = None
        return self._memory

    def _build_system_prompt(self, user_message: str) -> str:
        """Build system prompt with optional memory context."""
        memory_context = ""

        try:
            if self.memory and self.memory.is_available:
                context = self.memory.get_context_string(user_message, limit=3)
                if context:
                    memory_context = f"\n{context}\n"
        except Exception:
            pass

        return self.SYSTEM_PROMPT_TEMPLATE.format(memory_context=memory_context)

    def _build_messages(self, user_message: str) -> list[dict]:
        """Build message list with system prompt and history."""
        system_msg = {
            "role": "system",
            "content": self._build_system_prompt(user_message),
        }
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })
        
        # Keep last 10 exchanges to avoid token overflow
        recent_history = self.conversation_history[-20:]
        
        return [system_msg] + recent_history

    def _store_exchange(self, user_message: str, assistant_response: str) -> None:
        """Store conversation exchange in memory."""
        try:
            if self.memory and self.memory.is_available:
                self.memory.add_conversation([
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant_response},
                ])
        except Exception:
            pass

    async def send_message(self, message: str) -> str:
        """Send message and get complete response."""
        messages = self._build_messages(message)
        
        try:
            response = await acompletion(
                model=self.model,
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
            )
            
            assistant_content = response.choices[0].message.content
            
            # Store in conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_content,
            })
            
            # Store in persistent memory
            self._store_exchange(message, assistant_content)
            
            return assistant_content
            
        except Exception as e:
            # Show detailed error for debugging
            import traceback
            error_details = str(e)
            error_msg = f"[Backend error: {type(e).__name__}] {error_details}"
            return error_msg

    async def stream_message(self, message: str) -> AsyncIterator[str]:
        """Stream response token by token for real-time UI updates."""
        messages = self._build_messages(message)
        
        try:
            response = await acompletion(
                model=self.model,
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
                stream=True,
            )
            
            full_response = ""
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
            
            # Store complete response in history
            self.conversation_history.append({
                "role": "assistant",
                "content": full_response,
            })
            
            # Store in persistent memory
            self._store_exchange(message, full_response)
            
        except Exception as e:
            error_details = str(e)
            error_msg = f"[Backend error: {type(e).__name__}] {error_details}"
            yield error_msg

    def add_preference(self, preference: str, category: str = "general") -> bool:
        """Store a user preference in persistent memory."""
        if self.memory:
            return self.memory.add_preference(preference, category)
        return False

    def add_rejection(self, operation: str, reason: str) -> bool:
        """Store rejection reason for learning."""
        if self.memory:
            return self.memory.add_rejection(operation, reason)
        return False

    def clear_history(self) -> None:
        """Clear conversation history (not persistent memory)."""
        self.conversation_history.clear()

    @property
    def memory_available(self) -> bool:
        """Check if persistent memory is available."""
        return self.memory is not None and self.memory.is_available

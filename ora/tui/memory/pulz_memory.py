"""Persistent memory layer using Mem0 + Qdrant."""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class MemoryResult:
    """A single memory search result."""
    content: str
    score: float
    metadata: Dict[str, Any]


class PulZMemory:
    """
    Persistent memory layer for OrA using Mem0 + Qdrant vector store.
    
    Enables cross-session learning:
    - Store conversations and retrieve relevant context
    - Remember user preferences
    - Learn from rejections
    """

    def __init__(
        self,
        user_id: str = "randall",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
    ) -> None:
        self.user_id = user_id
        self._memory = None
        self._qdrant_host = qdrant_host
        self._qdrant_port = qdrant_port
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        """Lazy initialization of Mem0 connection."""
        if self._initialized:
            return True
        
        try:
            from mem0 import Memory
            
            config = {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "host": self._qdrant_host,
                        "port": self._qdrant_port,
                        "collection_name": f"ora_memory_{self.user_id}_v1",
                    },
                },
                "embedder": {
                    "provider": "ollama",
                    "config": {
                        "model": "nomic-embed-text:latest",
                    },
                },
                "llm": {
                    "provider": "ollama",
                    "config": {
                        "model": "qwen2.5-coder:3b",
                    },
                },
                "version": "v1.1",
            }
            
            self._memory = Memory.from_config(config)
            self._initialized = True
            return True
            
        except Exception:
            # Qdrant/Ollama not available - memory disabled
            return False

    def add_conversation(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
    ) -> bool:
        """
        Store a conversation exchange in memory.
        
        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            session_id: Optional session identifier for grouping
        
        Returns:
            True if stored successfully, False otherwise
        """
        if not self._ensure_initialized():
            return False
        
        try:
            metadata = {"source": "ora_chat"}
            if session_id:
                metadata["session_id"] = session_id
            
            self._memory.add(
                messages,
                user_id=self.user_id,
                metadata=metadata,
            )
            return True
        except Exception:
            return False

    def add_preference(self, preference: str, category: str = "general") -> bool:
        """
        Store a user preference that persists across sessions.
        
        Example: "I prefer Python over JavaScript"
        """
        if not self._ensure_initialized():
            return False
        
        try:
            self._memory.add(
                [{"role": "user", "content": preference}],
                user_id=self.user_id,
                metadata={"type": "preference", "category": category},
            )
            return True
        except Exception:
            return False

    def add_rejection(self, operation: str, reason: str) -> bool:
        """
        Store why a user rejected an operation (for learning).
        
        Example: operation="delete files", reason="I prefer archiving"
        """
        if not self._ensure_initialized():
            return False
        
        try:
            message = f"User rejected '{operation}' because: {reason}"
            self._memory.add(
                [{"role": "system", "content": message}],
                user_id=self.user_id,
                metadata={"type": "rejection", "operation": operation},
            )
            return True
        except Exception:
            return False

    def search(self, query: str, limit: int = 5) -> List[MemoryResult]:
        """
        Search for relevant memories based on query.
        
        Returns list of MemoryResult objects sorted by relevance.
        """
        if not self._ensure_initialized():
            return []
        
        try:
            results = self._memory.search(
                query,
                user_id=self.user_id,
                limit=limit,
            )
            
            return [
                MemoryResult(
                    content=r.get("memory", ""),
                    score=r.get("score", 0.0),
                    metadata=r.get("metadata", {}),
                )
                for r in results.get("results", [])
            ]
        except Exception:
            return []

    def get_context_string(self, query: str, limit: int = 3) -> str:
        """
        Get formatted context string from relevant memories.
        
        Useful for injecting into LLM system prompts.
        """
        memories = self.search(query, limit=limit)
        
        if not memories:
            return ""
        
        context_lines = ["Relevant context from memory:"]
        for mem in memories:
            context_lines.append(f"• {mem.content}")
        
        return "\n".join(context_lines)

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all memories for this user."""
        if not self._ensure_initialized():
            return []
        
        try:
            return self._memory.get_all(user_id=self.user_id)
        except Exception:
            return []

    def clear(self) -> bool:
        """Clear all memories for this user."""
        if not self._ensure_initialized():
            return False
        
        try:
            self._memory.delete_all(user_id=self.user_id)
            return True
        except Exception:
            return False

    @property
    def is_available(self) -> bool:
        """Check if memory system is available."""
        return self._ensure_initialized()

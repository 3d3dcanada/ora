"""Local LLM backend using Ollama for fast agentic fallback.

Optimized for Feb 2026 models with tool-use and web browsing capabilities.
"""

import os
import json
import httpx
from typing import AsyncIterator, Optional, List, Dict, Any

# Ollama runs OpenAI-compatible API on port 11434
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# Recommended models for Feb 2026 (agentic, tool-use, fast)
# Priority order - first available will be used
RECOMMENDED_MODELS = [
    "llama3.1:8b-instruct",       # Best for function calling
    "dolphin3:8b",                # Agentic, function calling, coding
    "qwen3:8b",                   # Versatile reasoning, agentic
    "deepseek-r1:7b",             # Math, programming, reasoning
    "phi4:latest",                # Fast, efficient for small tasks
    "mistral:7b-instruct",        # Good general purpose
]


class LocalBackend:
    """
    Local LLM backend using Ollama.
    
    Fast fallback when cloud APIs are unavailable or rate-limited.
    Supports tool/function calling for agentic capabilities.
    Auto-detects best available model from recommended list.
    """
    
    # System prompt for OrA personality with agentic capabilities
    SYSTEM_PROMPT = """You are OrA, an elite AI command center assistant running locally.

PERSONALITY: Street-smart, direct, elite execution mindset. "Do no harm" ethic.

CAPABILITIES:
- Execute terminal commands (bash, git, system tools)
- File operations (read, write, organize)
- Web research and browsing
- Code generation and analysis
- System monitoring and optimization

When asked to perform an action:
1. Analyze the request
2. Plan the steps
3. Execute or provide the command
4. Report results

Be concise. Be helpful. Be real."""

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: str = OLLAMA_BASE_URL,
    ) -> None:
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)
        self._available: Optional[bool] = None
        self._model: Optional[str] = model
        self._detected_model: Optional[str] = None

    @property
    def model(self) -> str:
        """Get the active model, auto-detecting if needed."""
        return self._model or self._detected_model or "llama3.1:8b-instruct"

    async def is_available(self) -> bool:
        """Check if Ollama is running and detect best available model."""
        if self._available is not None:
            return self._available
        
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                available_models = [m.get("name", "") for m in data.get("models", [])]
                
                if not available_models:
                    self._available = False
                    return False
                
                # Auto-detect best model from recommended list
                for recommended in RECOMMENDED_MODELS:
                    model_base = recommended.split(":")[0]
                    for available in available_models:
                        if model_base in available:
                            self._detected_model = available
                            self._available = True
                            return True
                
                # Use first available if no recommended found
                self._detected_model = available_models[0]
                self._available = True
                return True
                
        except Exception:
            pass
        
        self._available = False
        return False

    async def list_models(self) -> List[str]:
        """List available models in Ollama."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            pass
        return []

    async def send_message(
        self, 
        message: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Send message and get complete response. Supports tool definitions."""
        if not await self.is_available():
            return "[Ollama not available. Start with: ollama serve]"
        
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
                "stream": False,
            }
            
            # Add tools for function calling if provided
            if tools:
                payload["tools"] = tools
            
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            
            if response.status_code == 200:
                data = response.json()
                msg = data.get("message", {})
                
                # Check for tool calls
                if "tool_calls" in msg:
                    return json.dumps(msg["tool_calls"], indent=2)
                
                return msg.get("content", "No response")
            else:
                return f"[Ollama error: {response.status_code}]"
                
        except Exception as e:
            return f"[Local backend error: {type(e).__name__}: {str(e)[:100]}]"

    async def stream_message(self, message: str) -> AsyncIterator[str]:
        """Stream response token by token."""
        if not await self.is_available():
            yield "[Ollama not available. Start with: ollama serve]"
            return
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": message},
                    ],
                    "stream": True,
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            yield f"[Local backend error: {type(e).__name__}]"

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


# Terminal command library for agentic tasks
TERMINAL_COMMANDS = {
    # File operations
    "list_files": "ls -la",
    "list_tree": "tree -L 2",
    "find_files": "fd --type f",
    "find_large": "find . -type f -size +100M -exec ls -lh {} \\;",
    
    # System info
    "disk_usage": "df -h",
    "memory_usage": "free -h",
    "cpu_info": "lscpu | head -20",
    "processes": "ps aux --sort=-%mem | head -20",
    
    # Git operations
    "git_status": "git status",
    "git_log": "git log --oneline -10",
    "git_diff": "git diff --stat",
    "git_branches": "git branch -a",
    
    # Search
    "search_code": "rg --type-add 'code:*.{py,js,ts,go,rs}' -t code",
    "search_text": "rg -i",
    
    # Network
    "ports": "ss -tulpn",
    "connections": "ss -s",
    
    # Docker
    "docker_ps": "docker ps --format 'table {{.Names}}\\t{{.Image}}\\t{{.Status}}'",
    "docker_images": "docker images --format 'table {{.Repository}}\\t{{.Tag}}\\t{{.Size}}'",
}

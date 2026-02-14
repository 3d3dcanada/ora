"""
OrA Backend Configuration
"""

from pydantic_settings import BaseSettings
from pathlib import Path


class OraConfig(BaseSettings):
    """OrA configuration settings."""
    
    # Paths
    ora_root: Path = Path(__file__).parent.parent.parent  # /Ora-os/backend
    workspace_root: Path = Path.home() / "ora-workspace"
    vault_path: Path = Path.home() / ".ora" / "vault.enc"
    audit_db_path: Path = Path.home() / ".ora" / "audit.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    ws_port: int = 8001

    # LLM
    default_model: str = "nvidia_nim/deepseek-ai/deepseek-v3-2"
    ollama_base_url: str = "http://localhost:11434"

    # Security
    max_authority_level: int = 3  # Default max without escalation
    session_timeout: int = 3600

    # Memory (optional)
    qdrant_url: str = "http://localhost:6333"
    embedder_model: str = "nomic-embed-text:latest"
    memory_llm_model: str = "qwen2.5-coder:3b"

    # User
    user_name: str = "Randall"
    refresh_interval: float = 5.0
    max_chat_history: int = 500

    class Config:
        env_prefix = "ORA_"
        env_file = ".env"
        extra = "allow"  # Allow extra environment variables


# Global configuration instance
config = OraConfig()
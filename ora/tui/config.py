"""OrA application configuration."""

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class OrAConfig:
    user_name: str = "Randall"
    refresh_interval: float = 5.0
    max_chat_history: int = 500
    session_start: float = field(default_factory=time.time)

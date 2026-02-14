"""OrA's personality engine. Fallback responses when LLM is unavailable."""

import random
import time
from dataclasses import dataclass


@dataclass
class OrAResponse:
    text: str
    timestamp: float


class OrAPersona:
    """OrA's voice. Street-smart, direct, elite execution, 'do no harm.'"""

    GREETINGS = [
        "Hey {name}. Systems are live. What do you need?",
        "Welcome back, {name}. Everything's running smooth — what's the play?",
        "{name}. I'm here. Let's make something happen.",
        "All systems nominal, {name}. Ready when you are.",
    ]

    RESPONSES: dict = {
        "help": (
            "Here's what I can do:\n"
            "  /help   — show commands\n"
            "  /clear  — clear chat\n"
            "  /model  — current model info\n"
            "  /status — system stats\n"
            "  /reset  — clear conversation history\n"
            "  /memory — check memory status\n\n"
            "Or just talk to me, {name}. I'm wired up."
        ),
        "status": (
            "Check the monitor panel on the right →\n"
            "Live CPU/RAM/Disk via psutil. Type /status for inline."
        ),
        "default": [
            "Got it, {name}. Let me think on that.",
            "Copy that. Working on it.",
            "Understood. Give me a sec.",
            "On it, {name}.",
            "Roger. Processing.",
        ],
    }

    def __init__(self, user_name: str = "Randall") -> None:
        self.user_name = user_name

    def greeting(self) -> OrAResponse:
        text = random.choice(self.GREETINGS).format(name=self.user_name)
        return OrAResponse(text=text, timestamp=time.time())

    def respond(self, user_input: str) -> OrAResponse:
        lower = user_input.strip().lower()
        if lower in ("help", "?", "/help"):
            text = self.RESPONSES["help"].format(name=self.user_name)
        elif lower in ("status", "/status", "sys", "system"):
            text = self.RESPONSES["status"]
        else:
            text = random.choice(self.RESPONSES["default"]).format(name=self.user_name)
        return OrAResponse(text=text, timestamp=time.time())

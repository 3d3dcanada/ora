"""
MoneyModZ Gateway Enforcement
Port from Omni-Stack gateway/main.py

Hardened system prompt requiring deterministic, factual responses
Hard tool allowlist: Only approved tools can execute when MoneyModZ is active
Fail-closed audit: If logging fails, operation BLOCKED (not skipped)
Higher confidence thresholds (trust >= 0.95 for any action)
No creative/speculative responses allowed when active
Every output must cite evidence when active
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

from ..core.constitution import Constitution
from ..security.authority_kernel import AuthorityLevel
from ..audit.immutable_log import ImmutableAuditLog


class MoneyModZEnforcer:
    """
    MoneyModZ revenue-sensitive mode enforcer.
    
    When active:
    - Requires deterministic, factual responses only
    - Hard tool allowlist (only approved tools)
    - Higher confidence thresholds (trust >= 0.95)
    - No creative/speculative responses allowed
    - Fail-closed audit: If logging fails, operation BLOCKED
    - All requests get `moneymodz: true` metadata
    """
    
    def __init__(self, audit_log: ImmutableAuditLog, constitution: Constitution):
        self.audit_log = audit_log
        self.constitution = constitution
        
        # Configuration
        self.moneymodz_enabled = os.getenv("MONEYMODZ_ENABLED", "false").lower() == "true"
        self.moneymodz_audit_log = Path.home() / ".ora" / "moneymodz_audit.jsonl"
        self.moneymodz_system_prompt_path = Path(__file__).parent / "prompts" / "moneymodz_system.txt"
        
        # Hard tool allowlist for MoneyModZ mode
        self.allowed_tools: Set[str] = {
            "filesystem_read",
            "code_analyzer_read",
            "web_search",
            "api_query_get",
            "moneymodz_health_write"  # Special MoneyModZ health check tool
        }
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
        
        # MoneyModZ state (global toggle)
        self._active = False
        
    def _load_system_prompt(self) -> str:
        """Load MoneyModZ system prompt from file."""
        try:
            if self.moneymodz_system_prompt_path.exists():
                return self.moneymodz_system_prompt_path.read_text(encoding="utf-8")
            
            # Default MoneyModZ system prompt
            return """You are operating in MoneyModZ revenue-sensitive mode.

CRITICAL CONSTRAINTS:
1. You MUST provide ONLY deterministic, factual responses.
2. You MUST cite evidence for every claim (source URLs, file paths, line numbers).
3. You MUST NOT speculate, hypothesize, or provide creative solutions.
4. You MUST NOT use tools outside the MoneyModZ allowlist.
5. You MUST maintain confidence >= 0.95 for any action.
6. You MUST NOT generate code without explicit evidence of correctness.
7. You MUST NOT modify production systems without explicit approval.
8. You MUST log all operations with fail-closed audit trail.

RESPONSE FORMAT:
- Start with "MONEYMODZ: " prefix
- Cite evidence in [brackets] after each claim
- Include confidence score (0.0-1.0)
- End with audit trail reference

Example:
MONEYMODZ: The system is operational. [source: health_check.py:42] Confidence: 0.98. Audit: MMZ-2025-001"""
        except Exception:
            return "You are in MoneyModZ revenue mode."

    def is_moneymodz_mode(self, metadata: Optional[Dict[str, Any]]) -> bool:
        """Check if request is in MoneyModZ mode."""
        if not metadata:
            return False
        return metadata.get("mode") == "moneymodz" or metadata.get("moneymodz") is True

    def log_moneymodz_action(self, action: str, data: Dict[str, Any]) -> None:
        """
        Log MoneyModZ actions for audit trail.
        FAIL CLOSED: If logging fails, raise exception to block execution.
        """
        try:
            self.moneymodz_audit_log.parent.mkdir(parents=True, exist_ok=True)

            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                **data
            }

            # Write with explicit flush to ensure durability
            with self.moneymodz_audit_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
                f.flush()  # Force write to disk
                os.fsync(f.fileno())  # Force OS-level sync

        except Exception as e:
            # FAIL CLOSED: Logging failure blocks execution
            raise RuntimeError(f"CRITICAL: MoneyModZ audit logging failed: {e}") from e

    def inject_moneymodz_prompt(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepend MoneyModZ system prompt to messages."""
        system_message = {
            "role": "system",
            "content": self.system_prompt
        }

        # Check if there's already a system message
        if messages and messages[0].get("role") == "system":
            # Prepend to existing system message
            messages[0]["content"] = f"{self.system_prompt}\n\n{messages[0].get('content', '')}"
            return messages
        else:
            # Insert new system message at the beginning
            return [system_message] + messages

    def filter_moneymodz_tools(self, tools: Optional[List[Dict[str, Any]]], session_id: str = "unknown") -> Optional[List[Dict[str, Any]]]:
        """
        Filter tools to only MoneyModZ-approved ones in MoneyModZ mode.
        HARD ALLOWLIST - explicitly reject disallowed tools and log rejections.
        """
        if not tools:
            return tools

        allowed_tools = []
        rejected_tools = []

        for tool in tools:
            tool_name = tool.get("function", {}).get("name", "")
            if tool_name in self.allowed_tools:
                allowed_tools.append(tool)
            else:
                rejected_tools.append(tool_name)

        # Log all rejections (will fail closed if logging fails)
        if rejected_tools:
            self.log_moneymodz_action("tools_rejected", {
                "session_id": session_id,
                "rejected_tools": rejected_tools,
                "allowed_tools": list(self.allowed_tools),
                "reason": "Tools not in MoneyModZ allowlist"
            })

        return allowed_tools if allowed_tools else None

    def enforce_moneymodz_constraints(self, 
                                     request: Dict[str, Any], 
                                     session_id: str,
                                     agent_name: str = "unknown") -> Dict[str, Any]:
        """
        Apply MoneyModZ constraints to a request.
        Returns modified request with constraints applied.
        """
        metadata = request.get("metadata", {})
        in_moneymodz_mode = self.is_moneymodz_mode(metadata)
        
        if not in_moneymodz_mode:
            return request

        # Kill switch check
        if not self.moneymodz_enabled:
            self.log_moneymodz_action("mode_rejected", {
                "session_id": session_id,
                "agent": agent_name,
                "reason": "MoneyModZ globally disabled"
            })
            raise ValueError("MoneyModZ mode is currently disabled")

        # Log mode activation
        self.log_moneymodz_action("mode_activated", {
            "session_id": session_id,
            "agent": agent_name,
            "model": request.get("model", "unknown"),
            "has_tools": bool(request.get("tools"))
        })

        # Inject MoneyModZ system prompt
        if "messages" in request:
            request["messages"] = self.inject_moneymodz_prompt(request["messages"])

        # Filter tools to MoneyModZ-approved only
        if "tools" in request and request["tools"]:
            original_count = len(request["tools"])
            request["tools"] = self.filter_moneymodz_tools(request["tools"], session_id)
            filtered_count = len(request["tools"]) if request["tools"] else 0

            self.log_moneymodz_action("tools_filtered", {
                "session_id": session_id,
                "agent": agent_name,
                "original_count": original_count,
                "filtered_count": filtered_count
            })

        # Add MoneyModZ metadata
        if "metadata" not in request:
            request["metadata"] = {}
        request["metadata"]["moneymodz"] = True
        request["metadata"]["moneymodz_session"] = session_id

        # Enforce higher confidence threshold
        if "confidence_threshold" not in request:
            request["confidence_threshold"] = 0.95
        
        # Lower temperature for deterministic responses
        if "temperature" in request:
            request["temperature"] = min(request["temperature"], 0.3)
        else:
            request["temperature"] = 0.1

        return request

    def check_confidence_threshold(self, confidence: float, operation: str, session_id: str) -> bool:
        """Check if confidence meets MoneyModZ threshold."""
        if confidence < 0.95:
            self.log_moneymodz_action("confidence_rejected", {
                "session_id": session_id,
                "operation": operation,
                "confidence": confidence,
                "threshold": 0.95,
                "reason": "Confidence below MoneyModZ threshold"
            })
            return False
        return True

    def validate_evidence_citation(self, response: str, session_id: str) -> bool:
        """
        Validate that response contains evidence citations.
        Returns True if valid, False if missing citations.
        """
        # Check for evidence markers
        has_brackets = "[" in response and "]" in response
        has_source = "source:" in response.lower() or "evidence:" in response.lower()
        
        if not (has_brackets or has_source):
            self.log_moneymodz_action("evidence_missing", {
                "session_id": session_id,
                "response_preview": response[:100] if len(response) > 100 else response,
                "reason": "Missing evidence citations"
            })
            return False
        return True

    def set_active(self, active: bool):
        """Set MoneyModZ mode active/inactive globally."""
        self._active = active
        self.log_moneymodz_action("mode_toggled", {
            "active": active,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    @property
    def active(self) -> bool:
        """Get MoneyModZ mode active status."""
        return self._active
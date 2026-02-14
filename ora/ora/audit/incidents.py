"""
ora.audit.incidents
====================

Append-only incident tracker with two-strike protocol.

Tracks:
- Deployment failures
- Security gate blocks
- Agent errors
- User rejections

Two-strike protocol: 2 failures of the same type within a session
triggers human escalation and pauses automated operations.

Persists to JSONL file at ~/.ora/incidents.jsonl
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path.home() / ".ora" / "incidents.jsonl"


@dataclass
class Incident:
    id: str
    timestamp: str
    incident_type: str          # "deployment_failure" | "security_block" | "agent_error" | "user_rejection"
    description: str
    agent: Optional[str]
    operation: Optional[str]
    details: dict
    status: str = "open"        # "open" | "investigating" | "resolved"


@dataclass
class IncidentResolution:
    root_cause: str
    prevention_gate: str
    verified_at: str
    verified_by: str = "system"


@dataclass
class IncidentEntry:
    incident: Incident
    resolution: Optional[IncidentResolution] = None
    closed_at: Optional[str] = None


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class IncidentTracker:
    """
    Append-only incident log with two-strike protocol.

    Two-strike: if the same incident_type fires twice in the current
    session without resolution, `two_strike_triggered` is set to True
    and automated operations should be paused pending human review.
    """

    def __init__(self, path: Path = _DEFAULT_PATH) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._session_counts: dict[str, int] = {}
        self.two_strike_triggered: bool = False
        self._escalation_callbacks: list = []
        self._log: list[IncidentEntry] = []
        self._load()

    def _load(self) -> None:
        """Load existing incidents from JSONL file."""
        if not self._path.exists():
            return
        try:
            with open(self._path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    raw = json.loads(line)
                    inc = Incident(**raw["incident"])
                    res = None
                    if raw.get("resolution"):
                        res = IncidentResolution(**raw["resolution"])
                    entry = IncidentEntry(
                        incident=inc,
                        resolution=res,
                        closed_at=raw.get("closed_at"),
                    )
                    self._log.append(entry)
        except Exception as e:
            logger.warning(f"Failed to load incidents: {e}")

    def _append(self, entry: IncidentEntry) -> None:
        """Append a single entry to the JSONL file."""
        try:
            with open(self._path, "a") as f:
                f.write(json.dumps(asdict(entry)) + "\n")
        except Exception as e:
            logger.error(f"Failed to write incident: {e}")

    def _rewrite(self) -> None:
        """Rewrite the full JSONL file (used after resolution updates)."""
        try:
            with open(self._path, "w") as f:
                for entry in self._log:
                    f.write(json.dumps(asdict(entry)) + "\n")
        except Exception as e:
            logger.error(f"Failed to rewrite incidents: {e}")

    def record(
        self,
        incident_type: str,
        description: str,
        agent: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> str:
        """
        Record a new incident.

        Returns the incident ID.
        Applies two-strike protocol: if this type has fired twice this
        session, triggers escalation and pauses automated ops.
        """
        inc_id = f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        incident = Incident(
            id=inc_id,
            timestamp=_utcnow(),
            incident_type=incident_type,
            description=description,
            agent=agent,
            operation=operation,
            details=details or {},
        )
        entry = IncidentEntry(incident=incident)
        self._log.append(entry)
        self._append(entry)

        # Two-strike tracking
        self._session_counts[incident_type] = self._session_counts.get(incident_type, 0) + 1
        if self._session_counts[incident_type] >= 2 and not self.two_strike_triggered:
            self.two_strike_triggered = True
            logger.warning(
                f"TWO-STRIKE TRIGGERED: '{incident_type}' has failed twice this session. "
                "Automated operations paused — human review required."
            )
            for cb in self._escalation_callbacks:
                try:
                    cb(incident_type, inc_id)
                except Exception:
                    pass

        return inc_id

    def resolve(
        self,
        incident_id: str,
        root_cause: str,
        prevention_gate: str,
        verified_by: str = "operator",
    ) -> bool:
        """Mark an incident as resolved."""
        entry = next((e for e in self._log if e.incident.id == incident_id), None)
        if not entry:
            return False

        entry.resolution = IncidentResolution(
            root_cause=root_cause,
            prevention_gate=prevention_gate,
            verified_at=_utcnow(),
            verified_by=verified_by,
        )
        entry.incident.status = "resolved"
        entry.closed_at = _utcnow()
        self._rewrite()

        # Reset two-strike if all open incidents of that type are resolved
        incident_type = entry.incident.incident_type
        open_of_type = [
            e for e in self._log
            if e.incident.incident_type == incident_type
            and e.incident.status != "resolved"
        ]
        if not open_of_type:
            self._session_counts[incident_type] = 0
            if self.two_strike_triggered:
                # Check if ANY type still has open counts >= 2
                still_triggered = any(v >= 2 for v in self._session_counts.values())
                if not still_triggered:
                    self.two_strike_triggered = False
                    logger.info("Two-strike cleared — automated operations resumed.")

        return True

    def on_escalation(self, callback) -> None:
        """Register a callback fired when two-strike triggers."""
        self._escalation_callbacks.append(callback)

    def get_open(self) -> list[IncidentEntry]:
        """Return all unresolved incidents."""
        return [e for e in self._log if e.incident.status != "resolved"]

    def get_all(self) -> list[IncidentEntry]:
        """Return all incidents."""
        return list(self._log)

    def get_by_id(self, incident_id: str) -> Optional[IncidentEntry]:
        return next((e for e in self._log if e.incident.id == incident_id), None)

    def stats(self) -> dict:
        """Summary statistics."""
        resolved = [e for e in self._log if e.incident.status == "resolved"]
        open_inc = [e for e in self._log if e.incident.status == "open"]
        investigating = [e for e in self._log if e.incident.status == "investigating"]

        mttr_hours = 0.0
        if resolved:
            total_ms = 0
            for e in resolved:
                if e.closed_at and e.incident.timestamp:
                    start = datetime.fromisoformat(e.incident.timestamp)
                    end = datetime.fromisoformat(e.closed_at)
                    total_ms += (end - start).total_seconds() * 1000
            mttr_hours = (total_ms / len(resolved)) / (1000 * 60 * 60)

        return {
            "total": len(self._log),
            "open": len(open_inc),
            "investigating": len(investigating),
            "resolved": len(resolved),
            "mean_time_to_resolve_hours": round(mttr_hours, 2),
            "two_strike_active": self.two_strike_triggered,
            "session_counts": dict(self._session_counts),
        }

    def export_jsonl(self) -> str:
        """Export full log as JSONL string."""
        return "\n".join(json.dumps(asdict(e)) for e in self._log)


# Module-level singleton — lazy init
_tracker: Optional[IncidentTracker] = None


def get_tracker() -> IncidentTracker:
    """Get or create the global incident tracker."""
    global _tracker
    if _tracker is None:
        _tracker = IncidentTracker()
    return _tracker

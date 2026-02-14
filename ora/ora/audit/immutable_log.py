"""
OrA Immutable Audit Log - Tamper-evident audit logging system

Port from BUZZ Neural Core ImmutableAuditLog
"""

import os
import json
import hashlib
import hmac
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """Single audit log entry"""
    timestamp: str
    level: str
    action: str
    tool: str
    parameters: Dict
    authority: str
    result: str
    signature: str
    session_id: str
    user_id: str


class ImmutableAuditLog:
    """
    Tamper-evident audit logging system
    
    Each entry is signed with HMAC-SHA256 using a key derived from:
    - Previous entry's signature (chain)
    - Machine-specific hardware ID
    - Timestamp
    
    This creates a blockchain-like chain of entries where any
    modification invalidates subsequent signatures.
    """
    
    DB_PATH = Path.home() / ".ora" / "audit.db"
    
    def __init__(self):
        self._lock = threading.Lock()
        self._last_signature = "0" * 64  # Genesis hash
        self._init_db()
        self._load_last_signature()
    
    def _init_db(self):
        """Initialize the audit database"""
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    action TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    parameters TEXT,
                    authority TEXT NOT NULL,
                    result TEXT,
                    signature TEXT NOT NULL,
                    session_id TEXT,
                    user_id TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session ON audit_log(session_id)
            """)
            
            conn.commit()
    
    def _load_last_signature(self):
        """Load the last signature from database"""
        with sqlite3.connect(self.DB_PATH) as conn:
            cursor = conn.execute(
                "SELECT signature FROM audit_log ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                self._last_signature = row[0]
    
    def _derive_key(self) -> bytes:
        """Derive signing key from hardware and previous signature"""
        # Get hardware ID (simplified - use vault's hardware fingerprint)
        try:
            with open("/etc/machine-id") as f:
                machine_id = f.read().strip()
        except:
            machine_id = str(os.uname())
        
        # Combine with last signature
        material = f"{machine_id}:{self._last_signature}:{int(time.time() / 3600)}"
        return hashlib.sha256(material.encode()).digest()
    
    def _sign_entry(self, entry: Dict) -> str:
        """Create HMAC signature for entry"""
        key = self._derive_key()
        data = json.dumps(entry, sort_keys=True)
        signature = hmac.new(key, data.encode(), hashlib.sha256).hexdigest()
        return signature
    
    def log(self, level: str, action: str, tool: str, 
            parameters: Dict = None, authority: str = "A0",
            result: str = "pending", session_id: str = None,
            user_id: str = None) -> Optional[str]:
        """
        Add entry to immutable audit log
        
        Returns the signature of the entry for verification
        """
        with self._lock:
            entry_data = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "action": action,
                "tool": tool,
                "parameters": json.dumps(parameters or {}),
                "authority": authority,
                "result": result,
                "session_id": session_id or "default",
                "user_id": user_id or "anonymous"
            }
            
            # Sign the entry
            signature = self._sign_entry(entry_data)
            entry_data["signature"] = signature
            
            try:
                with sqlite3.connect(self.DB_PATH) as conn:
                    conn.execute("""
                        INSERT INTO audit_log 
                        (timestamp, level, action, tool, parameters, authority, result, signature, session_id, user_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry_data["timestamp"],
                        entry_data["level"],
                        entry_data["action"],
                        entry_data["tool"],
                        entry_data["parameters"],
                        entry_data["authority"],
                        entry_data["result"],
                        signature,
                        entry_data["session_id"],
                        entry_data["user_id"]
                    ))
                    conn.commit()
                
                # Update last signature for chaining
                self._last_signature = signature
                
                return signature
                
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")
                return None
    
    def verify_chain(self, limit: int = 1000) -> Dict:
        """
        Verify the integrity of the audit chain
        
        Returns dict with verification results
        """
        with sqlite3.connect(self.DB_PATH) as conn:
            cursor = conn.execute(
                """SELECT timestamp, level, action, tool, parameters, authority, result, signature, session_id, user_id
                   FROM audit_log ORDER BY id DESC LIMIT ?""",
                (limit,)
            )
            rows = cursor.fetchall()
        
        results = {
            "total_checked": len(rows),
            "valid": 0,
            "invalid": 0,
            "errors": []
        }
        
        prev_signature = None
        
        for row in reversed(rows):  # Check from oldest to newest
            timestamp, level, action, tool, parameters, authority, result, signature, session_id, user_id = row
            
            entry_data = {
                "timestamp": timestamp,
                "level": level,
                "action": action,
                "tool": tool,
                "parameters": parameters,
                "authority": authority,
                "result": result,
                "session_id": session_id,
                "user_id": user_id
            }
            
            # Recalculate signature
            expected_sig = self._sign_entry(entry_data)
            
            if expected_sig == signature:
                results["valid"] += 1
            else:
                results["invalid"] += 1
                results["errors"].append(f"Entry at {timestamp} has invalid signature")
            
            prev_signature = signature
        
        return results
    
    def query(self, start_time: str = None, end_time: str = None,
              level: str = None, tool: str = None, limit: int = 100) -> List[Dict]:
        """Query audit log entries"""
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        if level:
            query += " AND level = ?"
            params.append(level)
        if tool:
            query += " AND tool = ?"
            params.append(tool)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
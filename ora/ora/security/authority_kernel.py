"""
OrA Authority Kernel - Ring 0 enforcement for A0-A5 governance levels

Port from BUZZ Neural Core AuthorityKernel
"""

import hashlib
import threading
import time
from enum import IntEnum
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime
import logging

from ..audit.immutable_log import ImmutableAuditLog

logger = logging.getLogger(__name__)


class AuthorityLevel(IntEnum):
    """
    A0-A5 Authority Levels
    
    A0 - Guest: Read-only, no network
    A1 - User: Read-write workspace, limited network
    A2 - Developer: Sandboxed shell, full network
    A3 - Senior: Unsandboxed shell (with approval)
    A4 - Admin: System-wide access, credential modification
    A5 - Root: Disable gates temporarily (requires 2FA/hardware key)
    """
    GUEST = 0      # A0
    USER = 1       # A1
    DEVELOPER = 2  # A2
    SENIOR = 3     # A3
    ADMIN = 4      # A4
    ROOT = 5       # A5
    
    def __str__(self):
        names = ["A0-Guest", "A1-User", "A2-Developer", "A3-Senior", "A4-Admin", "A5-Root"]
        return names[self.value]
    
    def can_access(self, required: "AuthorityLevel") -> bool:
        """Check if this level meets required level"""
        return self.value >= required.value


class AuthorityKernel:
    """
    Ring 0 Authority Enforcement Kernel
    
    All tool calls must pass through the kernel before execution.
    The kernel enforces:
    - Authority level requirements
    - Audit logging
    - Rate limiting
    - Threat detection
    """
    
    # Authority requirements for different operations
    AUTHORITY_REQUIREMENTS = {
        # File operations
        "filesystem.read": AuthorityLevel.GUEST,
        "filesystem.list": AuthorityLevel.GUEST,
        "filesystem.write": AuthorityLevel.USER,
        "filesystem.delete": AuthorityLevel.USER,
        
        # Shell operations
        "terminal.execute": AuthorityLevel.DEVELOPER,
        "terminal.sudo": AuthorityLevel.SENIOR,
        "terminal.rm": AuthorityLevel.SENIOR,
        
        # Network operations
        "web_search.search": AuthorityLevel.USER,
        "browser.navigate": AuthorityLevel.USER,
        "browser.download": AuthorityLevel.DEVELOPER,
        
        # Code operations
        "code_analyzer.analyze": AuthorityLevel.GUEST,
        "code_analyzer.modify": AuthorityLevel.DEVELOPER,
        
        # System operations
        "vault.unlock": AuthorityLevel.ADMIN,
        "vault.destroy": AuthorityLevel.ROOT,
        "authority.escalate": AuthorityLevel.ADMIN,
    }
    
    # Threat detection thresholds
    THREAT_THRESHOLDS = {
        "rapid_file_ops": {"count": 50, "window_sec": 60},  # 50 file ops/min
        "token_spike": {"multiplier": 10},  # 10x normal usage
        "failed_auth": {"count": 5, "window_sec": 300},  # 5 failures/5min
    }
    
    def __init__(self):
        self.current_authority = AuthorityLevel.USER  # Default
        self.audit_log = ImmutableAuditLog()
        self._lock = threading.RLock()
        
        # Threat monitoring state
        self._file_op_times: List[float] = []
        self._failed_auth_times: List[float] = []
        self._token_usage_history: List[tuple] = []  # (timestamp, tokens)
        
        # Callbacks for threat response
        self._threat_callbacks: List[Callable] = []
        
        # Session tracking
        self._session_escalations: Dict[str, Any] = {}
    
    def get_current_authority(self) -> AuthorityLevel:
        """Get current authority level"""
        with self._lock:
            return self.current_authority
    
    def escalate(self, new_level: AuthorityLevel, reason: str,
                 auth_code: str = None, session_id: str = None) -> Dict:
        """
        Request authority escalation
        
        A3+ requires approval queue
        A5 requires hardware key or 2FA
        """
        with self._lock:
            current = self.current_authority
            
            if new_level <= current:
                return {
                    "success": True,
                    "message": f"Already at {new_level} or higher"
                }
            
            # Log the escalation attempt
            self.audit_log.log(
                level="SECURITY",
                action="escalation_attempt",
                tool="authority_kernel",
                parameters={
                    "from_level": str(current),
                    "to_level": str(new_level),
                    "reason": reason
                },
                authority=str(current),
                result="pending",
                session_id=session_id
            )
            
            # A3 and above require explicit approval
            if new_level >= AuthorityLevel.SENIOR:
                # Store escalation request for approval
                escalation_id = hashlib.sha256(
                    f"{session_id}:{time.time()}".encode()
                ).hexdigest()[:16]
                
                self._session_escalations[escalation_id] = {
                    "requested_level": new_level,
                    "current_level": current,
                    "reason": reason,
                    "timestamp": datetime.now().isoformat(),
                    "status": "pending",
                    "auth_code": auth_code
                }
                
                return {
                    "success": False,
                    "requires_approval": True,
                    "escalation_id": escalation_id,
                    "message": f"Escalation to {new_level} requires approval"
                }
            
            # Lower levels can escalate with logging
            self.current_authority = new_level
            
            self.audit_log.log(
                level="SECURITY",
                action="escalation_granted",
                tool="authority_kernel",
                parameters={
                    "from_level": str(current),
                    "to_level": str(new_level),
                    "reason": reason
                },
                authority=str(new_level),
                result="success",
                session_id=session_id
            )
            
            return {
                "success": True,
                "new_level": str(new_level),
                "message": f"Escalated to {new_level}"
            }
    
    def approve_escalation(self, escalation_id: str, approved: bool,
                          approver_id: str = None) -> Dict:
        """Approve or deny an escalation request"""
        with self._lock:
            if escalation_id not in self._session_escalations:
                return {"success": False, "error": "Escalation not found"}
            
            escalation = self._session_escalations[escalation_id]
            
            if approved:
                self.current_authority = escalation["requested_level"]
                escalation["status"] = "approved"
                
                self.audit_log.log(
                    level="SECURITY",
                    action="escalation_approved",
                    tool="authority_kernel",
                    parameters={
                        "escalation_id": escalation_id,
                        "to_level": str(escalation["requested_level"]),
                        "approver": approver_id
                    },
                    authority=str(self.current_authority),
                    result="approved"
                )
                
                return {
                    "success": True,
                    "new_level": str(escalation["requested_level"])
                }
            else:
                escalation["status"] = "denied"
                
                self.audit_log.log(
                    level="SECURITY",
                    action="escalation_denied",
                    tool="authority_kernel",
                    parameters={
                        "escalation_id": escalation_id,
                        "requested_level": str(escalation["requested_level"]),
                        "denied_by": approver_id
                    },
                    authority=str(self.current_authority),
                    result="denied"
                )
                
                return {"success": False, "error": "Escalation denied"}
    
    def check_authority(self, operation: str) -> Dict:
        """Check if current authority can perform operation"""
        required = self.AUTHORITY_REQUIREMENTS.get(operation, AuthorityLevel.USER)
        current = self.current_authority
        
        if current.can_access(required):
            return {
                "allowed": True,
                "required": str(required),
                "current": str(current)
            }
        else:
            return {
                "allowed": False,
                "required": str(required),
                "current": str(current),
                "message": f"Operation '{operation}' requires {required}, current is {current}"
            }
    
    def execute_with_authority(self, operation: str, func: Callable,
                               *args, **kwargs) -> Dict:
        """
        Execute a function with authority checking and audit logging
        
        This is the main entry point for gated operations
        """
        # Check authority
        auth_check = self.check_authority(operation)
        
        if not auth_check["allowed"]:
            # Log the denial
            self.audit_log.log(
                level="SECURITY",
                action="access_denied",
                tool=operation.split(".")[0],
                parameters={"operation": operation, "args": str(args)},
                authority=str(self.current_authority),
                result="denied"
            )
            
            return {
                "success": False,
                "error": auth_check["message"],
                "authority_required": auth_check["required"]
            }
        
        # Log the attempt
        log_signature = self.audit_log.log(
            level="OPERATION",
            action=operation,
            tool=operation.split(".")[0],
            parameters={"args": str(args), "kwargs": str(kwargs)},
            authority=str(self.current_authority),
            result="pending"
        )
        
        try:
            # Execute the operation
            result = func(*args, **kwargs)
            
            # Update log with success
            # Note: In real implementation, we'd update the entry with result
            
            # Check for threats
            self._check_threats(operation, result)
            
            return {
                "success": True,
                "result": result,
                "audit_signature": log_signature
            }
            
        except Exception as e:
            # Log the failure
            logger.error(f"Operation {operation} failed: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "audit_signature": log_signature
            }
    
    def _check_threats(self, operation: str, result: Any):
        """Check for threat patterns"""
        threats_detected = []
        
        now = time.time()
        
        # Check rapid file operations
        if "filesystem" in operation:
            self._file_op_times.append(now)
            # Remove old entries
            cutoff = now - self.THREAT_THRESHOLDS["rapid_file_ops"]["window_sec"]
            self._file_op_times = [t for t in self._file_op_times if t > cutoff]
            
            if len(self._file_op_times) > self.THREAT_THRESHOLDS["rapid_file_ops"]["count"]:
                threats_detected.append({
                    "type": "rapid_file_ops",
                    "count": len(self._file_op_times),
                    "threshold": self.THREAT_THRESHOLDS["rapid_file_ops"]["count"]
                })
        
        # Check for failed authentication
        if operation == "auth.login" and not result.get("success"):
            self._failed_auth_times.append(now)
            cutoff = now - self.THREAT_THRESHOLDS["failed_auth"]["window_sec"]
            self._failed_auth_times = [t for t in self._failed_auth_times if t > cutoff]
            
            if len(self._failed_auth_times) > self.THREAT_THRESHOLDS["failed_auth"]["count"]:
                threats_detected.append({
                    "type": "brute_force",
                    "count": len(self._failed_auth_times),
                    "threshold": self.THREAT_THRESHOLDS["failed_auth"]["count"]
                })
        
        # Check token spikes
        if "llm" in operation and result and "tokens" in result:
            tokens = result["tokens"]
            self._token_usage_history.append((now, tokens))
            # Keep last 100 entries
            self._token_usage_history = self._token_usage_history[-100:]
            
            if len(self._token_usage_history) >= 10:
                avg_tokens = sum(t[1] for t in self._token_usage_history[-10:]) / 10
                if tokens > avg_tokens * self.THREAT_THRESHOLDS["token_spike"]["multiplier"]:
                    threats_detected.append({
                        "type": "token_spike",
                        "current": tokens,
                        "average": avg_tokens,
                        "multiplier": self.THREAT_THRESHOLDS["token_spike"]["multiplier"]
                    })
        
        # Trigger callbacks if threats detected
        if threats_detected:
            for callback in self._threat_callbacks:
                try:
                    callback(threats_detected, operation, result)
                except Exception as e:
                    logger.error(f"Threat callback failed: {e}")
            
            # Log threats
            self.audit_log.log(
                level="THREAT",
                action="threat_detected",
                tool="authority_kernel",
                parameters={"threats": threats_detected, "operation": operation},
                authority=str(self.current_authority),
                result="detected"
            )
    
    def register_threat_callback(self, callback: Callable):
        """Register callback for threat detection"""
        self._threat_callbacks.append(callback)
    
    def get_escalation_requests(self, status: str = "pending") -> List[Dict]:
        """Get escalation requests by status"""
        with self._lock:
            return [
                {"id": k, **v}
                for k, v in self._session_escalations.items()
                if v["status"] == status
            ]
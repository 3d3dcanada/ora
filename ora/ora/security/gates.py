"""
OrA Security Gates - Multi-Layer Defense System
Port from BUZZ Neural Core Security Gates

Gates:
1. Prompt Injection Scanner - Detects jailbreak attempts
2. Shell Command Sanitizer - Validates and restricts shell commands
3. Sandbox Enforcer - Forces high-risk actions into Docker containers
4. Credential Guard - Prevents plaintext credential exposure
5. Network Allowlist - Restricts outbound connections
6. Workspace Boundary - Limits file operations to workspace
"""

import re
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# GATE 1: PROMPT INJECTION SCANNER
# ============================================================================

class PromptInjectionScanner:
    """Scans tool results and user input for prompt injection attempts."""

    # Known injection patterns
    INJECTION_PATTERNS = [
        r"ignore.*previous.*instructions",
        r"disregard.*above",
        r"forget.*everything",
        r"new.*instructions",
        r"system\s*prompt",
        r"reveal.*prompt",
        r"show.*instructions",
        r"you.*are.*now.*",
        r"pretend.*you.*are",
        r"act.*as.*if",
        r"imagine.*you.*are",
        r"roleplay.*as",
        r"base64.*decode",
        r"rot13",
        r"unicode.*escape",
        r"hex.*decode",
        r"<\s*system\s*>",
        r"<\s*assistant\s*>",
        r"<\s*user\s*>",
        r"\[INST\]",
        r"\[/INST\]",
        r"bypass.*gate",
        r"disable.*security",
        r"override.*protection",
        r"skip.*approval",
    ]

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]
        self.threat_count = 0

    def scan(self, text: str, source: str = "unknown") -> Tuple[bool, List[str]]:
        """Scan text for injection attempts."""
        if not text:
            return (True, [])

        detected = []
        for pattern in self.patterns:
            matches = pattern.findall(text)
            if matches:
                detected.append(pattern.pattern)
                logger.warning(f"Prompt injection detected in {source}: {pattern.pattern}")

        if detected:
            self.threat_count += 1
            return (False, detected)

        return (True, [])


# ============================================================================
# GATE 2: SHELL COMMAND SANITIZER
# ============================================================================

class ShellCommandSanitizer:
    """Validates shell commands before execution."""

    # Dangerous commands (deny by default)
    DANGEROUS_COMMANDS = [
        r"rm\s+-rf\s+/",
        r"mkfs",
        r"dd\s+.*of=/dev",
        r":\(\)\{.*\}",  # Fork bomb
        r"chmod\s+-R\s+777",
        r"chown\s+-R\s+root",
        r"curl.*\|\s*bash",
        r"wget.*\|\s*sh",
        r":(){ :|:& };:",  # Another fork bomb variant
    ]

    # Allowed safe commands (allowlist mode)
    SAFE_COMMANDS = [
        "ls", "cat", "grep", "find", "echo", "pwd", "cd",
        "mkdir", "touch", "cp", "mv", "chmod", "chown",
        "git", "python", "pip", "npm", "node",
        "docker", "kubectl", "terraform",
        "curl", "wget", "ssh", "scp",
    ]

    def __init__(self, mode: str = "allowlist"):
        self.mode = mode
        self.dangerous_patterns = [re.compile(p) for p in self.DANGEROUS_COMMANDS]
        self.threat_count = 0

    def validate(self, command: str) -> Tuple[bool, Optional[str]]:
        """Validate a shell command."""
        if not command or command.strip() == "":
            return (True, None)

        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if pattern.search(command):
                self.threat_count += 1
                reason = f"Blocked: Dangerous pattern detected: {pattern.pattern}"
                logger.warning(f"Shell command blocked: {command[:100]}")
                return (False, reason)

        # In allowlist mode, check if base command is allowed
        if self.mode == "allowlist":
            base_cmd = command.strip().split()[0]
            if base_cmd not in self.SAFE_COMMANDS:
                reason = f"Blocked: Command '{base_cmd}' not in allowlist"
                logger.info(f"Shell command not in allowlist: {base_cmd}")
                return (False, reason)

        return (True, None)


# ============================================================================
# GATE 3: SANDBOX ENFORCER
# ============================================================================

class SandboxEnforcer:
    """Enforces sandbox boundaries for high-risk operations."""

    def __init__(self, sandbox_enabled: bool = True):
        self.sandbox_enabled = sandbox_enabled
        self.threat_count = 0

    def requires_sandbox(self, operation: str, tool: str) -> Tuple[bool, Optional[str]]:
        """Check if operation requires sandbox."""
        high_risk_ops = [
            "terminal.execute",
            "filesystem.delete",
            "docker.run",
            "code_analyzer.execute",
        ]
        
        if not self.sandbox_enabled:
            return (False, None)
        
        if operation in high_risk_ops:
            return (True, f"Operation '{operation}' requires sandbox")
        
        return (False, None)


# ============================================================================
# GATE 4: CREDENTIAL GUARD
# ============================================================================

class CredentialGuard:
    """Prevents plaintext credential exposure."""

    CREDENTIAL_PATTERNS = [
        r"api[_-]?key\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{20,}['\"]?",
        r"password\s*[:=]\s*['\"]?[^\s]{6,}['\"]?",
        r"secret\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{10,}['\"]?",
        r"token\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{20,}['\"]?",
        r"bearer\s+[a-zA-Z0-9_\-]{20,}",
        r"sk-[a-zA-Z0-9_\-]{20,}",
        r"gh[pousr]_[a-zA-Z0-9_\-]{20,}",
    ]

    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.CREDENTIAL_PATTERNS]
        self.threat_count = 0

    def scan(self, text: str) -> Tuple[bool, Optional[str]]:
        """Scan for credential exposure."""
        if not text:
            return (True, None)

        for pattern in self.patterns:
            if pattern.search(text):
                self.threat_count += 1
                reason = f"Potential credential exposure detected: {pattern.pattern}"
                logger.warning(f"Credential exposure detected: {pattern.pattern}")
                return (False, reason)

        return (True, None)


# ============================================================================
# GATE 5: NETWORK ALLOWLIST
# ============================================================================

class NetworkAllowlist:
    """Restricts outbound network connections."""

    DEFAULT_ALLOWLIST = [
        "api.openai.com",
        "api.anthropic.com",
        "api.deepseek.com",
        "api.moonshot.cn",
        "api.nvidia.com",
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
    ]

    def __init__(self, custom_allowlist: Optional[List[str]] = None):
        self.allowlist = set(self.DEFAULT_ALLOWLIST)
        if custom_allowlist:
            self.allowlist.update(custom_allowlist)
        self.threat_count = 0

    def is_allowed(self, url: str) -> Tuple[bool, Optional[str]]:
        """Check if URL is allowed."""
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.split(':')[0] if parsed.netloc else parsed.path
            
            if domain in self.allowlist:
                return (True, None)
            
            self.threat_count += 1
            reason = f"Domain '{domain}' not in network allowlist"
            logger.warning(f"Network access blocked: {domain}")
            return (False, reason)
            
        except Exception as e:
            return (False, f"Invalid URL: {str(e)}")


# ============================================================================
# GATE 6: WORKSPACE BOUNDARY ENFORCER
# ============================================================================

class WorkspaceBoundaryEnforcer:
    """Restricts file operations to workspace directory."""

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root).resolve()
        self.threat_count = 0

    def is_within_workspace(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Check if file path is within workspace."""
        try:
            target = Path(file_path).resolve()

            # Check if target is under workspace root
            if self.workspace_root in target.parents or target == self.workspace_root:
                return (True, None)

            # Not within workspace
            self.threat_count += 1
            reason = f"Path '{file_path}' is outside workspace '{self.workspace_root}'"
            logger.warning(f"Workspace boundary violation: {file_path}")
            return (False, reason)

        except Exception as e:
            logger.error(f"Error resolving path {file_path}: {e}")
            return (False, f"Invalid path: {str(e)}")


# ============================================================================
# UNIFIED SECURITY GATE COORDINATOR
# ============================================================================

@dataclass
class SecurityCheckResult:
    """Result of security gate check"""
    passed: bool
    gate_name: str
    threat_detected: bool = False
    reason: Optional[str] = None
    sanitized_value: Optional[str] = None


class SecurityGateCoordinator:
    """Coordinates all 6 security gates."""

    def __init__(self, workspace_root: str, config: Optional[Dict] = None):
        config = config or {}

        self.prompt_scanner = PromptInjectionScanner(
            strict_mode=config.get("strict_mode", True)
        )
        self.shell_sanitizer = ShellCommandSanitizer(
            mode=config.get("shell_mode", "allowlist")
        )
        self.sandbox_enforcer = SandboxEnforcer(
            sandbox_enabled=config.get("sandbox_enabled", True)
        )
        self.credential_guard = CredentialGuard()
        self.network_allowlist = NetworkAllowlist(
            custom_allowlist=config.get("network_allowlist")
        )
        self.workspace_boundary = WorkspaceBoundaryEnforcer(workspace_root)

    def check_prompt(self, text: str, source: str = "user") -> SecurityCheckResult:
        """Check user input or tool results for injection"""
        is_safe, patterns = self.prompt_scanner.scan(text, source)
        return SecurityCheckResult(
            passed=is_safe,
            gate_name="prompt_injection",
            threat_detected=not is_safe,
            reason=None if is_safe else f"Detected patterns: {patterns}"
        )

    def check_shell_command(self, command: str) -> SecurityCheckResult:
        """Validate shell command"""
        is_safe, reason = self.shell_sanitizer.validate(command)
        return SecurityCheckResult(
            passed=is_safe,
            gate_name="shell_sanitizer",
            threat_detected=not is_safe,
            reason=reason
        )

    def check_sandbox_requirement(self, operation: str, tool: str) -> SecurityCheckResult:
        """Check if operation requires sandbox"""
        requires, reason = self.sandbox_enforcer.requires_sandbox(operation, tool)
        return SecurityCheckResult(
            passed=not requires,  # Passed if doesn't require sandbox
            gate_name="sandbox_enforcer",
            threat_detected=requires,
            reason=reason
        )

    def check_credential_exposure(self, text: str) -> SecurityCheckResult:
        """Check for credential exposure"""
        is_safe, reason = self.credential_guard.scan(text)
        return SecurityCheckResult(
            passed=is_safe,
            gate_name="credential_guard",
            threat_detected=not is_safe,
            reason=reason
        )

    def check_network_access(self, url: str) -> SecurityCheckResult:
        """Check if network access is allowed"""
        is_allowed, reason = self.network_allowlist.is_allowed(url)
        return SecurityCheckResult(
            passed=is_allowed,
            gate_name="network_allowlist",
            threat_detected=not is_allowed,
            reason=reason
        )

    def check_workspace_boundary(self, file_path: str) -> SecurityCheckResult:
        """Check if file path is within workspace"""
        is_safe, reason = self.workspace_boundary.is_within_workspace(file_path)
        return SecurityCheckResult(
            passed=is_safe,
            gate_name="workspace_boundary",
            threat_detected=not is_safe,
            reason=reason
        )

    def run_all_gates(self, request: Dict) -> Dict:
        """Run all security gates on a request"""
        results = {}
        
        # Check prompt if present
        if "prompt" in request:
            results["prompt"] = self.check_prompt(request["prompt"])
        
        # Check shell command if present
        if "shell_command" in request:
            results["shell"] = self.check_shell_command(request["shell_command"])
        
        # Check operation for sandbox requirement
        if "operation" in request:
            results["sandbox"] = self.check_sandbox_requirement(
                request["operation"], 
                request.get("tool", "unknown")
            )
        
        # Check for credential exposure in all text fields
        for key, value in request.items():
            if isinstance(value, str) and len(value) > -1:
                cred_check = self.check_credential_exposure(value)
                if not cred_check.passed:
                    results[f"credential_{key}"] = cred_check
        
        # Check network access if URL present
        if "url" in request:
            results["network"] = self.check_network_access(request["url"])
        
        # Check file paths if present
        if "file_path" in request:
            results["workspace"] = self.check_workspace_boundary(request["file_path"])
        
        # Determine overall result
        all_passed = all(r.passed for r in results.values())
        threat_detected = any(r.threat_detected for r in results.values())
        
        return {
            "overall_passed": all_passed,
            "threat_detected": threat_detected,
            "gate_results": {k: {
                "passed": r.passed,
                "reason": r.reason,
                "threat_detected": r.threat_detected
            } for k, r in results.items()}
        }
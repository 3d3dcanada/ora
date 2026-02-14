"""
OrA Security Module
"""

from .vault import OraVault
from .authority_kernel import AuthorityKernel
from .gates import (
    PromptInjectionScanner,
    ShellCommandSanitizer,
    SandboxEnforcer,
    CredentialGuard,
    NetworkAllowlist,
    WorkspaceBoundaryEnforcer,
    SecurityGateCoordinator,
    SecurityCheckResult,
)

__all__ = [
    "OraVault",
    "AuthorityKernel",
    "PromptInjectionScanner",
    "ShellCommandSanitizer",
    "SandboxEnforcer",
    "CredentialGuard",
    "NetworkAllowlist",
    "WorkspaceBoundaryEnforcer",
    "SecurityGateCoordinator",
    "SecurityCheckResult",
]
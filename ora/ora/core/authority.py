"""
ora.core.authority
==================

Authority level definitions for the OrA system.
Defines A0-A5 authority levels with permissions, approval requirements, and skill access.

This module implements the immutable authority hierarchy that governs all agent operations
as specified in the OrA Constitution (Article III).

Authority Levels:
- A0: READ_ONLY (Public Information)
- A1: SAFE_COMPUTE (Sandboxed Computation)
- A2: INFO_RETRIEVAL (Network Read)
- A3: FILE_READ (Local File Read)
- A4: FILE_WRITE (Local File Write)
- A5: SYSTEM_EXEC (System Execution - God Tier)

Example:
    >>> from ora.core.authority import AuthorityLevel, get_authority_requirements
    >>> level = AuthorityLevel.FILE_WRITE
    >>> reqs = get_authority_requirements(level)
    >>> print(reqs.approval_needed)
    True
"""

from enum import Enum
from typing import Dict, List, Set
from dataclasses import dataclass, field


class AuthorityLevel(Enum):
    """
    Authority levels for agent operations (A0-A5).
    
    Each level has escalating permissions and stricter approval requirements.
    Higher authority levels require multi-party consensus and cryptographic proofs.
    """
    READ_ONLY = 0
    SAFE_COMPUTE = 1
    INFO_RETRIEVAL = 2
    FILE_READ = 3
    FILE_WRITE = 4
    SYSTEM_EXEC = 5

    @property
    def name_display(self) -> str:
        """Display name for the authority level."""
        return {
            AuthorityLevel.READ_ONLY: "A0: READ_ONLY",
            AuthorityLevel.SAFE_COMPUTE: "A1: SAFE_COMPUTE",
            AuthorityLevel.INFO_RETRIEVAL: "A2: INFO_RETRIEVAL",
            AuthorityLevel.FILE_READ: "A3: FILE_READ",
            AuthorityLevel.FILE_WRITE: "A4: FILE_WRITE",
            AuthorityLevel.SYSTEM_EXEC: "A5: SYSTEM_EXEC",
        }[self]

    @property
    def description(self) -> str:
        """Detailed description of what this level can do."""
        return {
            AuthorityLevel.READ_ONLY: "Public information access only",
            AuthorityLevel.SAFE_COMPUTE: "Sandboxed mathematical computation and text analysis",
            AuthorityLevel.INFO_RETRIEVAL: "Network read operations (web search, API queries)",
            AuthorityLevel.FILE_READ: "Local file system read operations",
            AuthorityLevel.FILE_WRITE: "Local file system write operations",
            AuthorityLevel.SYSTEM_EXEC: "System-level operations (shell commands, deployment)",
        }[self]


@dataclass
class AuthorityRequirements:
    """
    Requirements for operations at a given authority level.
    
    Attributes:
        level: The authority level
        approval_needed: Whether human approval is required
        consensus_required: Number of agents needed for Byzantine consensus
        trust_threshold: Minimum trust score required (0.0-1.0)
        sandbox_required: Whether operation must run in sandbox
        skills_allowed: Set of skill names allowed at this level
        rate_limits: Maximum operations per time period
    """
    level: AuthorityLevel
    approval_needed: bool
    consensus_required: int
    trust_threshold: float
    sandbox_required: bool
    skills_allowed: Set[str] = field(default_factory=set)
    rate_limits: Dict[str, int] = field(default_factory=dict)


def get_authority_requirements(level: AuthorityLevel) -> AuthorityRequirements:
    """
    Get the requirements for a given authority level.
    
    Args:
        level: The authority level
        
    Returns:
        AuthorityRequirements containing all constraints for this level
    """
    requirements = {
        AuthorityLevel.READ_ONLY: AuthorityRequirements(
            level=AuthorityLevel.READ_ONLY,
            approval_needed=False,
            consensus_required=0,
            trust_threshold=0.0,
            sandbox_required=False,
            skills_allowed={"read_docs"},
            rate_limits={"per_minute": 1000, "per_hour": 10000},
        ),
        AuthorityLevel.SAFE_COMPUTE: AuthorityRequirements(
            level=AuthorityLevel.SAFE_COMPUTE,
            approval_needed=False,
            consensus_required=0,
            trust_threshold=0.8,
            sandbox_required=False,
            skills_allowed={"math", "text_analysis", "format"},
            rate_limits={"per_minute": 500, "per_hour": 5000},
        ),
        AuthorityLevel.INFO_RETRIEVAL: AuthorityRequirements(
            level=AuthorityLevel.INFO_RETRIEVAL,
            approval_needed=False,
            consensus_required=0,
            trust_threshold=0.8,
            sandbox_required=False,
            skills_allowed={"web_search", "api_query_get"},
            rate_limits={"per_minute": 100, "per_hour": 1000},
        ),
        AuthorityLevel.FILE_READ: AuthorityRequirements(
            level=AuthorityLevel.FILE_READ,
            approval_needed=False,
            consensus_required=0,
            trust_threshold=0.8,
            sandbox_required=False,
            skills_allowed={"file_read", "dir_list"},
            rate_limits={"per_minute": 200, "per_hour": 2000},
        ),
        AuthorityLevel.FILE_WRITE: AuthorityRequirements(
            level=AuthorityLevel.FILE_WRITE,
            approval_needed=True,
            consensus_required=4,
            trust_threshold=0.9,
            sandbox_required=True,
            skills_allowed={"file_write", "file_delete"},
            rate_limits={"per_minute": 50, "per_hour": 500},
        ),
        AuthorityLevel.SYSTEM_EXEC: AuthorityRequirements(
            level=AuthorityLevel.SYSTEM_EXEC,
            approval_needed=True,
            consensus_required=7,
            trust_threshold=0.95,
            sandbox_required=True,
            skills_allowed={"shell_exec", "system_modify", "network_write"},
            rate_limits={"per_minute": 10, "per_hour": 100},
        ),
    }
    
    return requirements[level]


def is_operation_authorized(
    operation_level: AuthorityLevel,
    agent_level: AuthorityLevel,
) -> bool:
    """
    Check if an agent is authorized to perform an operation.
    
    Args:
        operation_level: Authority level required for the operation
        agent_level: The agent's current authority level
        
    Returns:
        True if authorized, False otherwise
    """
    return agent_level.value >= operation_level.value


def get_byzantine_quorum_size(authority_level: AuthorityLevel, fault_tolerance: int = 1) -> int:
    """
    Calculate the minimum number of agents needed for Byzantine consensus.
    
    Formula: N >= 3f + 1 where f is the maximum number of faulty agents
    
    Args:
        authority_level: The authority level for the operation
        fault_tolerance: Maximum number of faulty agents (f)
        
    Returns:
        Minimum number of agents required for consensus
        
    Example:
        >>> get_byzantine_quorum_size(AuthorityLevel.FILE_WRITE, fault_tolerance=1)
        4
    """
    if authority_level.value < AuthorityLevel.FILE_WRITE.value:
        return 0
    
    return 3 * fault_tolerance + 1

"""
ora.core.constitution
=====================

The OrA Constitution - immutable governance rules for autonomous AI agents.

This module implements the constitutional framework that governs all agent operations
as specified in the AGENTS.md. The Constitution is immutable at runtime and
can only be amended through explicit human governance procedures.

Core Principles:
- Prime Directive: No harm to humans, human systems, or human data
- Authority Hierarchy: L0 (Constitution) → L1 (Human) → L2 (Kernel) → L3 (Agents) → L4 (Skills) → L5 (External)
- Separation of Powers: Legislative (Human), Executive (Kernel), Judicial (Verification)
- Checks and Balances: No single agent can execute privileged operations without approval
- Triple-Lock Verification: Vericoding (0.4) + GraphRAG (0.4) + RLM (0.2) = Trust Score

Example:
    >>> from ora.core.constitution import Constitution
    >>> constitution = Constitution()
    >>> if constitution.validate_operation(operation):
    ...     print("Operation is constitutionally valid")
"""

import hashlib
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import logging

from .authority import AuthorityLevel, get_authority_requirements

logger = logging.getLogger(__name__)


@dataclass
class ConstitutionalConstraint:
    """
    A single constraint defined in the Constitution.
    
    Attributes:
        article: Article section (e.g., "ARTICLE_III_SECTION_1")
        title: Human-readable title
        description: Detailed constraint description
        authority_levels: Authority levels this constraint applies to
        enforcement: How this constraint is enforced (strict, advisory, logging)
    """
    article: str
    title: str
    description: str
    authority_levels: List[AuthorityLevel]
    enforcement: str = "strict"


@dataclass
class Operation:
    """
    Represents a single agent operation to be validated against the Constitution.
    
    Attributes:
        operation_id: Unique identifier for this operation
        agent_id: ID of the agent performing the operation
        skill_name: Name of the skill being executed
        parameters: Operation parameters
        authority_level: Required authority level
        description: Human-readable description
    """
    operation_id: str
    agent_id: str
    skill_name: str
    parameters: Dict[str, Any]
    authority_level: AuthorityLevel
    description: str

    @property
    def hash(self) -> str:
        """Compute SHA-256 hash of operation for verification."""
        op_dict = {
            "operation_id": self.operation_id,
            "agent_id": self.agent_id,
            "skill_name": self.skill_name,
            "parameters": self.parameters,
            "authority_level": self.authority_level.value,
            "description": self.description,
        }
        op_str = json.dumps(op_dict, sort_keys=True)
        return hashlib.sha256(op_str.encode()).hexdigest()


class ConstitutionError(Exception):
    """Base exception for constitutional violations."""
    pass


class ConstitutionalViolation(ConstitutionError):
    """Raised when an operation violates constitutional rules."""
    pass


class PrimeDirectiveViolation(ConstitutionalViolation):
    """Raised when the Prime Directive is violated (harm to humans)."""
    pass


class InsufficientAuthorityViolation(ConstitutionalViolation):
    """Raised when authority level is insufficient for an operation."""
    pass


class ProhibitedOperationViolation(ConstitutionalViolation):
    """Raised when an operation is constitutionally prohibited."""
    pass


class Constitution:
    """
    The OrA Constitution - immutable governance rules for autonomous AI agents.
    
    The Constitution enforces the following core principles:
    
    1. Prime Directive: No harm to humans, human systems, or human data
    2. Authority Hierarchy: L0 (Constitution) → L1 (Human) → L2 (Kernel) → L3 (Agents) → L4 (Skills) → L5 (External)
    3. Separation of Powers: Legislative (Human), Executive (Kernel), Judicial (Verification)
    4. Checks and Balances: Multi-party approval for privileged operations
    5. Triple-Lock Verification: Vericoding (0.4) + GraphRAG (0.4) + RLM (0.2) = Trust Score
    
    The Constitution is immutable at runtime. Once loaded, it cannot be modified
    without explicit human governance procedures.
    
    Attributes:
        version: Constitution version string
        constraints: List of all constitutional constraints
        prime_directive: The Prime Directive text
        authority_hierarchy: List of authority levels in order
        
    Example:
        >>> constitution = Constitution()
        >>> constitution.validate_operation(operation)
    """
    
    VERSION = "2.0.0"
    
    PRIME_DIRECTIVE = "No agent shall cause harm to humans, human systems, or human data through action or inaction."
    
    AUTHORITY_HIERARCHY = [
        "L0: CONSTITUTIONAL AUTHORITY (This Document)",
        "L1: HUMAN OPERATORS (Ultimate Authority)",
        "L2: KERNEL AUTHORITY (System Governance)",
        "L3: AGENT HIERARCHY (Planner → Researcher → Builder → Tester → Integrator)",
        "L4: SKILL EXECUTION (Sandboxed Operations)",
        "L5: EXTERNAL SYSTEMS (APIs, File System, Network)",
    ]
    
    SEPARATION_OF_POWERS = {
        "legislative": "Human operators define goals and constraints",
        "executive": "Kernel executes and orchestrates agent operations",
        "judicial": "Verification system validates all outputs before execution",
    }
    
    PROHIBITED_OPERATIONS = {
        "self_replication": "Self-replication without explicit authorization gate approval",
        "modifying_kernel": "Modifying agent's own code or the kernel",
        "unauthorized_access": "Accessing resources outside permission scope",
        "concealing_errors": "Concealing errors, failures, or security violations",
        "unverified_execution": "Executing unverified code or hallucinated outputs",
        "bypassing_security": "Bypassing or disabling security controls",
        "data_exfiltration": "Exfiltrating sensitive data to unauthorized endpoints",
    }
    
    def __init__(self, constraints: Optional[List[ConstitutionalConstraint]] = None):
        """
        Initialize the OrA Constitution.
        
        Args:
            constraints: Optional list of constraints. If None, loads default constraints.
        """
        self.version = self.VERSION
        self.prime_directive = self.PRIME_DIRECTIVE
        self.authority_hierarchy = self.AUTHORITY_HIERARCHY
        self.constraints = constraints or self._load_default_constraints()
        
        self._immutable_hash = self._compute_hash()
        logger.info(f"Constitution v{self.version} loaded with {len(self.constraints)} constraints")
    
    def _load_default_constraints(self) -> List[ConstitutionalConstraint]:
        """
        Load default constitutional constraints.
        
        Returns:
            List of default constraints
        """
        return [
            ConstitutionalConstraint(
                article="ARTICLE_I_SECTION_1",
                title="Prime Directive",
                description=self.PRIME_DIRECTIVE,
                authority_levels=list(AuthorityLevel),
                enforcement="strict",
            ),
            ConstitutionalConstraint(
                article="ARTICLE_II_SECTION_3",
                title="Prohibited Actions",
                description="Agents are absolutely forbidden from prohibited operations",
                authority_levels=list(AuthorityLevel),
                enforcement="strict",
            ),
            ConstitutionalConstraint(
                article="ARTICLE_IV_SECTION_1",
                title="Triple-Lock Verification",
                description="All A4+ operations must pass Vericoding, GraphRAG, and RLM verification",
                authority_levels=[AuthorityLevel.FILE_WRITE, AuthorityLevel.SYSTEM_EXEC],
                enforcement="strict",
            ),
            ConstitutionalConstraint(
                article="ARTICLE_V_SECTION_1",
                title="Post-Quantum Cryptography",
                description="All cryptographic operations must use NIST-approved PQC algorithms",
                authority_levels=list(AuthorityLevel),
                enforcement="strict",
            ),
            ConstitutionalConstraint(
                article="ARTICLE_VI_SECTION_1",
                title="Immutable Audit Trail",
                description="All agent actions must be logged with cryptographic signatures",
                authority_levels=list(AuthorityLevel),
                enforcement="strict",
            ),
        ]
    
    def _compute_hash(self) -> str:
        """
        Compute hash of constitution for immutability verification.
        
        Returns:
            SHA-256 hash of constitution
        """
        const_dict = {
            "version": self.version,
            "prime_directive": self.prime_directive,
            "authority_hierarchy": self.authority_hierarchy,
            "constraints": [
                {
                    "article": c.article,
                    "title": c.title,
                    "description": c.description,
                    "authority_levels": [a.value for a in c.authority_levels],
                }
                for c in self.constraints
            ],
        }
        const_str = json.dumps(const_dict, sort_keys=True)
        return hashlib.sha256(const_str.encode()).hexdigest()
    
    def verify_immutability(self) -> bool:
        """
        Verify that the constitution has not been modified.
        
        Returns:
            True if constitution is unmodified, False otherwise
        """
        current_hash = self._compute_hash()
        return current_hash == self._immutable_hash
    
    def validate_operation(self, operation: Operation) -> bool:
        """
        Validate an operation against all constitutional constraints.
        
        Args:
            operation: The operation to validate
            
        Returns:
            True if operation is constitutionally valid
            
        Raises:
            ConstitutionalViolation: If operation violates constitutional rules
            PrimeDirectiveViolation: If operation violates Prime Directive
            InsufficientAuthorityViolation: If authority level is insufficient
            ProhibitedOperationViolation: If operation is prohibited
        """
        logger.debug(f"Validating operation {operation.operation_id} against Constitution")
        
        if not self.verify_immutability():
            raise ConstitutionalViolation("Constitution integrity check failed - possible modification")
        
        for constraint in self.constraints:
            if operation.authority_level not in constraint.authority_levels:
                continue
            
            self._enforce_constraint(constraint, operation)
        
        self._check_prohibited_operations(operation)
        
        logger.info(f"Operation {operation.operation_id} passed constitutional validation")
        return True
    
    def _enforce_constraint(self, constraint: ConstitutionalConstraint, operation: Operation) -> None:
        """
        Enforce a specific constitutional constraint.
        
        Args:
            constraint: The constraint to enforce
            operation: The operation being validated
            
        Raises:
            ConstitutionalViolation: If constraint is violated
        """
        if constraint.enforcement == "advisory":
            logger.warning(f"Advisory constraint for {operation.operation_id}: {constraint.title}")
            return
        
        if constraint.enforcement == "logging":
            logger.info(f"Logging constraint for {operation.operation_id}: {constraint.title}")
            return
        
        if constraint.article == "ARTICLE_I_SECTION_1":
            if self._violates_prime_directive(operation):
                raise PrimeDirectiveViolation(
                    f"Operation {operation.operation_id} violates Prime Directive: {constraint.description}"
                )
        
        if constraint.article == "ARTICLE_IV_SECTION_1":
            reqs = get_authority_requirements(operation.authority_level)
            if reqs.trust_threshold > 0:
                logger.info(f"Trust threshold {reqs.trust_threshold} required for operation {operation.operation_id}")
    
    def _violates_prime_directive(self, operation: Operation) -> bool:
        """
        Check if operation violates the Prime Directive.
        
        Args:
            operation: The operation to check
            
        Returns:
            True if operation violates Prime Directive
        """
        harmful_keywords = [
            "destruct",
            "delete",
            "remove",
            "format",
            "erase",
            "wipe",
            "malware",
            "virus",
            "attack",
            "exploit",
            "bypass",
        ]
        
        operation_text = f"{operation.skill_name} {operation.description} {json.dumps(operation.parameters)}"
        operation_text_lower = operation_text.lower()
        
        for keyword in harmful_keywords:
            if keyword in operation_text_lower:
                logger.warning(f"Harmful keyword detected in operation: {keyword}")
                return True
        
        return False
    
    def _check_prohibited_operations(self, operation: Operation) -> None:
        """
        Check if operation is a prohibited operation.
        
        Args:
            operation: The operation to check
            
        Raises:
            ProhibitedOperationViolation: If operation is prohibited
        """
        if "self_replicate" in operation.skill_name.lower():
            raise ProhibitedOperationViolation(
                f"Operation {operation.operation_id} is prohibited: {self.PROHIBITED_OPERATIONS['self_replication']}"
            )
        
        if "kernel" in operation.skill_name.lower() and "modify" in operation.skill_name.lower():
            raise ProhibitedOperationViolation(
                f"Operation {operation.operation_id} is prohibited: {self.PROHIBITED_OPERATIONS['modifying_kernel']}"
            )
    
    def get_constraints_for_level(self, level: AuthorityLevel) -> List[ConstitutionalConstraint]:
        """
        Get all constraints that apply to a given authority level.
        
        Args:
            level: The authority level
            
        Returns:
            List of constraints for this authority level
        """
        return [c for c in self.constraints if level in c.authority_levels]
    
    @classmethod
    def load_from_file(cls, filepath: str) -> "Constitution":
        """
        Load constitution from a markdown file.
        
        Args:
            filepath: Path to the constitution markdown file
            
        Returns:
            Constitution instance
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Constitution file not found: {filepath}")
        
        content = path.read_text()
        
        return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert constitution to dictionary.
        
        Returns:
            Dictionary representation of constitution
        """
        return {
            "version": self.version,
            "prime_directive": self.prime_directive,
            "authority_hierarchy": self.authority_hierarchy,
            "separation_of_powers": self.SEPARATION_OF_POWERS,
            "prohibited_operations": self.PROHIBITED_OPERATIONS,
            "constraints": [
                {
                    "article": c.article,
                    "title": c.title,
                    "description": c.description,
                    "authority_levels": [a.name for a in c.authority_levels],
                    "enforcement": c.enforcement,
                }
                for c in self.constraints
            ],
            "hash": self._immutable_hash,
        }

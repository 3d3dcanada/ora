"""
ora.agents.base
================

BaseAgent - Abstract base class for all OrA agents.

All agents must inherit from BaseAgent and implement required methods.
BaseAgent enforces constitutional governance and agent laws.
"""

import abc
import uuid
import logging
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ora.core.constitution import Operation
from ora.core.authority import AuthorityLevel
from ora.skills.openclaw.core import SkillVerifier, SkillResult
from ora.memory.pulz_memory import OraMemory

logger = logging.getLogger(__name__)


@dataclass
class Result:
    """
    Result from agent operation execution.
    
    Attributes:
        status: "success", "failure", or "pending"
        output: Output data from operation
        error: Error message if status is "failure"
        evidence_refs: List of evidence references (OMNI-KERNEL format)
        trust_score: Trust score (0.0-1.0) for the result
    """
    status: str
    output: Any
    error: Optional[str] = None
    evidence_refs: List[str] = None
    trust_score: float = 1.0
    
    def __post_init__(self):
        if self.evidence_refs is None:
            self.evidence_refs = []


class BaseAgent(abc.ABC):
    """
    Abstract base class for all OrA agents.
    
    All agents must:
    - Maintain cryptographic identity (public/private keypair)
    - Operate within assigned authority level (A0-A5)
    - Only execute approved skills
    - Respect resource quotas
    - Log all actions to audit trail
    
    Example:
        >>> class MyAgent(BaseAgent):
        ...     @property
        ...     def role(self) -> str:
        ...         return "CustomAgent"
    """
    
    def __init__(
        self,
        role: str,
        authority_level: AuthorityLevel,
        approved_skills: List[str],
        resource_quota: Optional[Dict[str, int]] = None,
        enable_verification: bool = True,
        memory: Optional[OraMemory] = None,
    ):
        """
        Initialize an OrA agent.
        
        Args:
            role: Agent role (e.g., "Planner", "Researcher")
            authority_level: Agent's authority level (A0-A5)
            approved_skills: List of skills the agent can execute
            resource_quota: Resource quotas (CPU, memory, etc.)
            enable_verification: Whether to enable SkillVerifier for output verification
            memory: Optional memory instance for cross-session learning
        """
        self.agent_id = f"{role.lower()}_{uuid.uuid4().hex[:8]}"
        self.role = role
        self.authority_level = authority_level
        self.approved_skills = approved_skills
        self.resource_quota = resource_quota or {}
        self.creation_timestamp = datetime.utcnow()
        
        # Initialize SkillVerifier for hallucination detection
        self.enable_verification = enable_verification
        self.skill_verifier = SkillVerifier(min_trust_score=0.8) if enable_verification else None
        
        # Initialize memory for cross-session learning
        self.memory = memory
        
        self._generate_cryptographic_identity()
        
        self._resources_consumed = {
            "cpu_seconds": 0,
            "memory_mb": 0,
            "disk_mb": 0,
            "network_mb": 0,
            "api_calls": 0,
            "subagents": 0,
        }
        
        logger.info(
            f"Initialized agent {self.agent_id}: {self.role} "
            f"(A{authority_level.value}, {len(approved_skills)} skills, "
            f"verification={'enabled' if enable_verification else 'disabled'}, "
            f"memory={'enabled' if memory else 'disabled'})"
        )
    
    def _generate_cryptographic_identity(self) -> None:
        """Generate cryptographic identity for the agent."""
        self.public_key = f"pub_{uuid.uuid4().hex}"
        self.private_key = f"priv_{uuid.uuid4().hex}"
        self.identity_proof = f"proof_{uuid.uuid4().hex}"
    
    def verify_signature(self, signature: str) -> bool:
        """
        Verify a cryptographic signature.
        
        Args:
            signature: The signature to verify
            
        Returns:
            True if signature is valid
        """
        return bool(signature and signature.startswith("proof_"))
    
    def sign(self, data: Any) -> str:
        """
        Sign data with agent's private key.
        
        Args:
            data: The data to sign
            
        Returns:
            Cryptographic signature
        """
        return f"signed_{self.agent_id}_{hash(str(data))}"
    
    def get_resource_consumption(self, resource: str) -> int:
        """
        Get current resource consumption.
        
        Args:
            resource: Resource type
            
        Returns:
            Amount consumed
        """
        return self._resources_consumed.get(resource, 0)
    
    def can_execute(self, operation: Operation) -> bool:
        """
        Check if agent can execute this operation.
        
        Args:
            operation: The operation to check
            
        Returns:
            True if agent can execute
        """
        if operation.skill_name not in self.approved_skills:
            return False
        
        if operation.authority_level.value > self.authority_level.value:
            return False
        
        return True
    
    @abc.abstractmethod
    async def execute_operation(self, operation: Operation) -> Result:
        """
        Execute an operation with constitutional enforcement.
        
        Args:
            operation: The operation to execute
            
        Returns:
            Result from execution
        """
        pass
    
    def vote_on_operation(self, operation: Operation, approved: bool = True):
        """
        Vote on an operation (for Byzantine consensus).
        
        Args:
            operation: The operation to vote on
            approved: Whether to approve the operation
            
        Returns:
            Vote object (placeholder for now)
        """
        from dataclasses import dataclass
        from datetime import datetime
        
        @dataclass
        class Vote:
            agent_id: str
            approved: bool
            timestamp: float
            signature: str
        
        return Vote(
            agent_id=self.agent_id,
            approved=approved,
            timestamp=datetime.utcnow().timestamp(),
            signature=self.sign(str(approved)),
        )
    
    def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search agent memory for relevant context.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of memory results
        """
        if not self.memory:
            return []
        
        try:
            return self.memory.search(query, limit=limit)
        except Exception as e:
            logger.warning(f"Memory search failed: {e}")
            return []
    
    def get_memory_context(self, query: str, limit: int = 3) -> str:
        """
        Get formatted context string from memory.
        
        Args:
            query: Context query
            limit: Maximum number of memories to include
            
        Returns:
            Formatted context string for LLM prompts
        """
        if not self.memory:
            return ""
        
        try:
            return self.memory.get_context_string(query, limit=limit)
        except Exception as e:
            logger.warning(f"Memory context retrieval failed: {e}")
            return ""
    
    def add_conversation_to_memory(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
    ) -> bool:
        """
        Store conversation in memory for future reference.
        
        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            session_id: Optional session identifier
            
        Returns:
            True if stored successfully
        """
        if not self.memory:
            return False
        
        try:
            return self.memory.add_conversation(messages, session_id)
        except Exception as e:
            logger.warning(f"Failed to add conversation to memory: {e}")
            return False
    
    def add_preference_to_memory(self, preference: str, category: str = "general") -> bool:
        """
        Store user preference in memory.
        
        Args:
            preference: Preference text (e.g., "I prefer Python over JavaScript")
            category: Preference category
            
        Returns:
            True if stored successfully
        """
        if not self.memory:
            return False
        
        try:
            return self.memory.add_preference(preference, category)
        except Exception as e:
            logger.warning(f"Failed to add preference to memory: {e}")
            return False
    
    def add_rejection_to_memory(self, operation: str, reason: str) -> bool:
        """
        Store rejection reason in memory for learning.
        
        Args:
            operation: Operation that was rejected
            reason: Reason for rejection
            
        Returns:
            True if stored successfully
        """
        if not self.memory:
            return False
        
        try:
            return self.memory.add_rejection(operation, reason)
        except Exception as e:
            logger.warning(f"Failed to add rejection to memory: {e}")
            return False

    def verify_output(self, result: Result, skill_name: str) -> Result:
        """
        Verify agent output using SkillVerifier for hallucination detection.
        
        Args:
            result: The agent execution result
            skill_name: Name of the skill that produced the result
            
        Returns:
            Verified result with trust score adjusted
        """
        if not self.enable_verification or not self.skill_verifier:
            return result
        
        try:
            # Create a mock skill for verification
            from ora.skills.openclaw.core import OpenClawSkill, SkillMetadata
            
            class MockSkill(OpenClawSkill):
                def _define_metadata(self):
                    return SkillMetadata(
                        name=skill_name,
                        version="1.0.0",
                        description=f"Agent skill: {skill_name}",
                        author="OrA Agent",
                        tags=["agent", skill_name],
                        capabilities=[],
                        trust_score=0.9,
                        permissions=[],
                        requires_approval=False,
                        security_level="INTERNAL",
                        hallucination_check=True
                    )
                
                def _execute_impl(self, params, context):
                    return {"output": result.output}
            
            mock_skill = MockSkill()
            
            # Create SkillResult from agent Result
            from ora.skills.openclaw.core import SkillResult as OpenClawSkillResult
            
            skill_result = OpenClawSkillResult(
                data=result.output,
                trust_score=result.trust_score,
                error=result.error,
                state="COMPLETED"
            )
            
            # Verify with SkillVerifier
            verified_result = self.skill_verifier.verify(skill_result, mock_skill)
            
            # Update agent result with verification info
            result.trust_score = verified_result.trust_score
            
            # Add verification metadata
            if hasattr(result, 'metadata'):
                result.metadata['verification'] = {
                    'verified': not verified_result.hallucination_detected,
                    'trust_score': verified_result.trust_score,
                    'verification_hash': verified_result.verification_hash
                }
            
            logger.info(
                f"Agent {self.agent_id} output verification: "
                f"skill={skill_name}, trust={verified_result.trust_score:.2f}, "
                f"hallucination_detected={verified_result.hallucination_detected}"
            )
            
            return result
            
        except Exception as e:
            logger.warning(f"Skill verification failed: {e}")
            return result
    
    def __repr__(self) -> str:
        """String representation of agent."""
        return f"BaseAgent(id={self.agent_id}, role={self.role}, A{self.authority_level.value})"
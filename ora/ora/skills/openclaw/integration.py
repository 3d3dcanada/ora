#!/usr/bin/env python3
"""
OPENCLAW INTEGRATION - OrA Skill Engine
Pattern: Complete OpenClaw ecosystem integration for OrA
Reference: OpenClaw Ecosystem adapted for OrA unified backend
===========================================================

Integrates:
- OpenClaw core (skills, hierarchies, messages)
- OrA tools (filesystem, terminal, code_analyzer, web_search)
- OrA security gates and authority kernel
- OrA audit logging
- Skill sandbox (isolated testing)
- Skill verification (hallucination detection)
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

# OpenClaw core
from .core import (
    SkillOrchestrator, SkillHierarchy, SkillMessageBus,
    SkillVerifier, SkillResult, SkillExecutionContext,
    SkillActionType, OpenClawSkill
)

# God-tier skills
from .god_tier import (
    GOD_TIER_SKILLS, register_all_skills,
    WebSearchSkill, PcFileSkill, PcShellSkill,
    VibeCoderSkill, CodeReviewSkill, GitOpsSkill,
    ReplicatorSkill, GateControlSkill
)

logger = logging.getLogger("OPENCLAW.INTEGRATION")


class OpenClawEngine:
    """
    Complete OpenClaw skill engine for OrA.
    Provides unified interface to all OpenClaw capabilities integrated with OrA.
    """
    
    def __init__(
        self,
        enable_sandbox: bool = True,
        cache_dir: str = "./.ora/openclaw_cache"
    ):
        self.enable_sandbox = enable_sandbox
        
        # Core OpenClaw components
        self.orchestrator = SkillOrchestrator()
        self.hierarchy = SkillHierarchy()
        self.message_bus = SkillMessageBus()
        self.verifier = SkillVerifier(min_trust_score=0.8)
        
        # OrA integration components (will be set during initialization)
        self.ora_tools_available = False
        self.security_gates = None
        self.authority_kernel = None
        self.audit_log = None
        
        # Skill registry
        self._skills: Dict[str, OpenClawSkill] = {}
        self._initialized = False
        
        # Create cache directory
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"OpenClawEngine initialized with cache: {self.cache_dir}")
    
    def initialize_with_ora(self, ora_components: Dict[str, Any]) -> bool:
        """
        Initialize OpenClaw with OrA components.
        
        Args:
            ora_components: Dictionary containing OrA components:
                - tools: OrA tools module
                - security_gates: SecurityGateCoordinator
                - authority_kernel: AuthorityKernel
                - audit_log: ImmutableAuditLog
        
        Returns:
            bool: True if initialization successful
        """
        try:
            # Import OrA tools if available
            from ora.tools import (
                FilesystemTool, TerminalTool, 
                CodeAnalyzerTool, WebSearchTool
            )
            self.ora_tools_available = True
            logger.info("OrA tools available for OpenClaw integration")
        except ImportError:
            logger.warning("OrA tools not available, using placeholder implementations")
            self.ora_tools_available = False
        
        # Store OrA components
        self.security_gates = ora_components.get("security_gates")
        self.authority_kernel = ora_components.get("authority_kernel")
        self.audit_log = ora_components.get("audit_log")
        
        # Register all god-tier skills
        skill_count = register_all_skills(self.orchestrator)
        
        self._initialized = True
        logger.info(f"OpenClawEngine initialized with {skill_count} skills")
        return True
    
    def execute_skill_with_authority(
        self,
        skill_id: str,
        params: Dict[str, Any],
        user: str = "system",
        authority_level: int = 1
    ) -> SkillResult:
        """
        Execute skill with OrA authority checks.
        
        Args:
            skill_id: Skill identifier
            params: Skill parameters
            user: User requesting execution
            authority_level: User's authority level (A0-A5)
        
        Returns:
            SkillResult: Execution result with verification
        """
        if not self._initialized:
            return SkillResult(
                skill_id=skill_id,
                success=False,
                error="OpenClawEngine not initialized",
                state="FAILED"
            )
        
        # Check authority if authority kernel available
        if self.authority_kernel:
            operation = f"skill_execute:{skill_id}"
            authorized, reason = self.authority_kernel.check_authority(
                operation=operation,
                authority_required=authority_level,
                user=user
            )
            
            if not authorized:
                return SkillResult(
                    skill_id=skill_id,
                    success=False,
                    error=f"Authority check failed: {reason}",
                    state="FAILED"
                )
        
        # Check security gates if available
        if self.security_gates:
            security_check = self.security_gates.check_input(params)
            if not security_check.passed:
                return SkillResult(
                    skill_id=skill_id,
                    success=False,
                    error=f"Security gate blocked: {security_check.blocked_reason}",
                    state="FAILED"
                )
        
        # Create execution context
        context = SkillExecutionContext(
            approval_required=(authority_level >= 4),  # A4+ requires approval
            encryption_enabled=True
        )
        
        # Execute skill
        result = self.orchestrator.execute_skill(skill_id, params, context)
        
        # Log to audit if available
        if self.audit_log and result.success:
            self.audit_log.log(
                action=f"skill_executed:{skill_id}",
                actor={"type": "user", "id": user},
                details={
                    "skill_id": skill_id,
                    "params": params,
                    "result": result.data,
                    "authority_level": authority_level
                }
            )
        
        return result
    
    def execute_skill_pipeline(
        self,
        skill_ids: List[str],
        initial_params: Dict[str, Any],
        user: str = "system",
        authority_level: int = 1
    ) -> List[SkillResult]:
        """
        Execute skills in pipeline with OrA integration.
        
        Args:
            skill_ids: List of skill IDs to execute in order
            initial_params: Initial parameters
            user: User requesting execution
            authority_level: User's authority level
        
        Returns:
            List[SkillResult]: Results for each skill in pipeline
        """
        results = []
        params = initial_params.copy()
        
        for skill_id in skill_ids:
            result = self.execute_skill_with_authority(
                skill_id=skill_id,
                params=params,
                user=user,
                authority_level=authority_level
            )
            
            results.append(result)
            
            if not result.success:
                logger.warning(f"Skill {skill_id} failed, stopping pipeline")
                break
            
            # Use output as next input if it's a dictionary
            if isinstance(result.data, dict):
                params.update(result.data)
        
        return results
    
    def get_skill_info(self, skill_id: str) -> Dict[str, Any]:
        """Get information about a skill"""
        skill = self._skills.get(skill_id)
        if not skill:
            return {"error": f"Skill not found: {skill_id}"}
        
        stats = skill.get_stats()
        metadata = skill.metadata
        
        return {
            "id": skill_id,
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "author": metadata.author,
            "tags": metadata.tags,
            "trust_score": metadata.trust_score,
            "requires_approval": metadata.requires_approval,
            "security_level": metadata.security_level.value,
            "stats": stats
        }
    
    def list_skills(self) -> List[Dict[str, Any]]:
        """List all registered skills"""
        skills_info = []
        
        for skill_id, skill in self._skills.items():
            metadata = skill.metadata
            skills_info.append({
                "id": skill_id,
                "name": metadata.name,
                "description": metadata.description,
                "trust_score": metadata.trust_score,
                "requires_approval": metadata.requires_approval,
                "security_level": metadata.security_level.value
            })
        
        return skills_info
    
    def register_custom_skill(
        self,
        skill: OpenClawSkill,
        parent_id: Optional[str] = None
    ) -> bool:
        """Register custom skill with engine"""
        if not self._initialized:
            return False
        
        success = self.orchestrator.register_skill(skill, parent_id)
        if success:
            self._skills[skill.metadata.id] = skill
            logger.info(f"Registered custom skill: {skill.metadata.name}")
        
        return success
    
    def verify_skill_output(
        self,
        skill_id: str,
        output: Any,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify skill output for hallucinations and correctness.
        
        Args:
            skill_id: Skill identifier
            output: Skill output to verify
            context: Verification context
        
        Returns:
            Dict with verification results
        """
        skill = self._skills.get(skill_id)
        if not skill:
            return {"verified": False, "error": f"Skill not found: {skill_id}"}
        
        # Create a mock result for verification
        mock_result = SkillResult(
            skill_id=skill_id,
            success=True,
            data=output,
            trust_score=skill.metadata.trust_score
        )
        
        # Verify with SkillVerifier
        verified_result = self.verifier.verify(mock_result, skill)
        
        return {
            "verified": not verified_result.hallucination_detected,
            "trust_score": verified_result.trust_score,
            "hallucination_detected": verified_result.hallucination_detected,
            "verification_hash": verified_result.verification_hash
        }


# Global engine instance
_engine_instance: Optional[OpenClawEngine] = None

def get_engine() -> OpenClawEngine:
    """Get singleton OpenClawEngine instance"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = OpenClawEngine()
    return _engine_instance


def initialize_ora_integration(ora_components: Dict[str, Any]) -> bool:
    """
    Initialize OpenClaw with OrA components (convenience function).
    
    Args:
        ora_components: Dictionary of OrA components
        
    Returns:
        bool: True if initialization successful
    """
    engine = get_engine()
    return engine.initialize_with_ora(ora_components)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'OpenClawEngine',
    'get_engine',
    'initialize_ora_integration',
]
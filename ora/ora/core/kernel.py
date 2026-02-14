"""
ora.core.kernel
===============

OraKernel - Central orchestration kernel for the OrA system.

The OraKernel is the central orchestration engine that enforces the Constitution,
manages the agent fleet, coordinates operations across interfaces, and maintains
the audit trail. It is the L2 authority in the governance hierarchy.

Architecture:
    Interfaces → Kernel → Agent Fleet → Skills → External Systems
         ↓         ↓          ↓            ↓           ↓
    WebUI,    Constitution, Byzantine,  Sandbox,   APIs,
    CLI,      Verification, Consensus,  Isolation, FileSystem,
    Discord,  Approval     Voting               Network
    WhatsApp, Gates
    Voice

Example:
    >>> from ora.core.kernel import OraKernel
    >>> from ora.core.constitution import Constitution
    >>> constitution = Constitution()
    >>> kernel = OraKernel(constitution)
    >>> response = await kernel.process_command("Search for recent AI papers", user="Randall")
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import json

# Import API client for real LLM calls
from ..clients.api_client import get_api_client, APIClient, TaskType, LLMResponse

from .constitution import Constitution, Operation, ConstitutionalViolation, PrimeDirectiveViolation, ProhibitedOperationViolation
from .authority import AuthorityLevel, get_authority_requirements

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """
    Alert/notification from the kernel.
    
    Attributes:
        severity: Alert severity ('info', 'warning', 'critical')
        message: Alert message
        timestamp: When the alert was generated
        source: Source of the alert
    """
    severity: str
    message: str
    timestamp: str
    source: str = "kernel"


@dataclass
class KernelResult:
    """
    Result from kernel processing.
    
    Attributes:
        status: Status of the operation (success, rejected, error, blocked)
        output: Response text or result
        operation_id: ID of the operation
        authority_required: Authority level required
        requires_approval: Whether approval is needed
        approval_id: ID for approval if required
        error: Error message if applicable
    """
    status: str
    output: str
    operation_id: str
    authority_required: AuthorityLevel
    requires_approval: bool = False
    approval_id: Optional[str] = None
    error: Optional[str] = None


class OraKernel:
    """
    Central orchestration kernel for OrA system.
    
    The kernel is responsible for:
    - Enforcing the Constitution
    - Managing the agent fleet
    - Coordinating operations across interfaces
    - Maintaining the audit trail
    - Handling emergency shutdowns
    
    Thread Safety:
        All methods are async-safe and can be called concurrently.
    """
    
    def __init__(
        self,
        constitution: Constitution,
        audit_logger: Optional[Any] = None,
        authority_kernel: Optional[Any] = None,
        security_gates: Optional[Any] = None,
    ):
        """
        Initialize the kernel with a Constitution.
        
        Args:
            constitution: The Constitution to enforce
            audit_logger: Optional audit logger instance
            authority_kernel: Optional authority kernel for A0-A5 enforcement
            security_gates: Optional security gate coordinator
            
        Raises:
            ValueError: If constitution is invalid
        """
        if not constitution.verify_immutability():
            raise ValueError("Constitution immutability check failed")
        
        self.constitution = constitution
        self.audit_logger = audit_logger
        self.authority_kernel = authority_kernel
        self.security_gates = security_gates
        
        self.agent_fleet: List[Any] = []
        self.active_interfaces: List[Any] = []
        self._running = False
        self._shutdown_requested = False
        
        self._operation_history: Dict[str, Operation] = {}
        self._metrics: Dict[str, Any] = {
            'operations_executed': 0,
            'operations_failed': 0,
            'operations_rejected': 0,
            'operations_blocked': 0,
            'start_time': datetime.utcnow(),
        }
        
        logger.info(f"OraKernel initialized with constitution v{constitution.version}")
    
    def register_interface(self, interface: Any) -> None:
        """
        Register a new interface adapter.
        
        Args:
            interface: The interface adapter to register
        """
        self.active_interfaces.append(interface)
        logger.info(f"Registered interface: {interface.__class__.__name__}")
    
    def register_agent(self, agent: Any) -> None:
        """
        Register an agent in the fleet.
        
        Args:
            agent: The agent to register
        """
        self.agent_fleet.append(agent)
        logger.info(f"Registered agent: {agent.agent_id} ({agent.role})")
    
    def parse_command(self, command: str, user: str = "unknown") -> Operation:
        """
        Parse a natural language command into an Operation.
        
        Args:
            command: The natural language command
            user: The user issuing the command
            
        Returns:
            Operation object
        """
        command_lower = command.lower()
        
        skill_name = "unknown"
        authority_level = AuthorityLevel.READ_ONLY
        parameters = {}
        
        if "search" in command_lower or "web" in command_lower or "find" in command_lower:
            skill_name = "web_search"
            authority_level = AuthorityLevel.INFO_RETRIEVAL
            parameters = {"query": command}
        elif "read" in command_lower or "file" in command_lower:
            skill_name = "file_read"
            authority_level = AuthorityLevel.FILE_READ
            parameters = {"path": command.split("file")[-1].strip() if "file" in command_lower else ""}
        elif "write" in command_lower or "save" in command_lower or "create" in command_lower:
            skill_name = "file_write"
            authority_level = AuthorityLevel.FILE_WRITE
            parameters = {"content": command}
        elif "execute" in command_lower or "run" in command_lower or "shell" in command_lower:
            skill_name = "shell_exec"
            authority_level = AuthorityLevel.SYSTEM_EXEC
            parameters = {"command": command}
        elif "calculate" in command_lower or "compute" in command_lower or "math" in command_lower:
            skill_name = "math"
            authority_level = AuthorityLevel.SAFE_COMPUTE
            parameters = {"expression": command}
        elif "delete" in command_lower or "remove" in command_lower:
            skill_name = "file_delete"
            authority_level = AuthorityLevel.FILE_WRITE
            parameters = {"path": command}
        elif "analyze" in command_lower or "review" in command_lower:
            skill_name = "code_analyzer"
            authority_level = AuthorityLevel.FILE_READ
            parameters = {"query": command}
        else:
            # Default to research/info retrieval
            skill_name = "research"
            authority_level = AuthorityLevel.INFO_RETRIEVAL
            parameters = {"query": command}
        
        operation_id = f"op_{uuid.uuid4().hex[:12]}"
        
        return Operation(
            operation_id=operation_id,
            agent_id=user,
            skill_name=skill_name,
            parameters=parameters,
            authority_level=authority_level,
            description=command,
        )
    
    async def process_command(
        self,
        command: str,
        user: str = "Randall",
    ) -> KernelResult:
        """
        Process a command from any interface.
        
        Args:
            command: The command text
            user: The user issuing the command
            
        Returns:
            KernelResult with status, output, and metadata
        """
        operation_id = f"op_{uuid.uuid4().hex[:12]}"
        
        try:
            # Parse command into operation
            operation = self.parse_command(command, user)
            operation_id = operation.operation_id
            
            logger.info(f"Processing operation {operation_id}: {command}")
            
            # Store in history
            self._operation_history[operation_id] = operation
            
            # Run security gates if available
            if self.security_gates:
                gate_result = self.security_gates.run_all_gates({
                    "type": "command",
                    "content": command,
                    "user": user,
                })
                if not gate_result.passed:
                    self._metrics['operations_blocked'] += 1
                    return KernelResult(
                        status="blocked",
                        output=f"Security gate blocked: {gate_result.blocked_reason}",
                        operation_id=operation_id,
                        authority_required=operation.authority_level,
                        error=gate_result.blocked_reason,
                    )
            
            # Validate against constitution
            try:
                self.constitution.validate_operation(operation)
            except PrimeDirectiveViolation as e:
                self._metrics['operations_blocked'] += 1
                await self._broadcast_alert(Alert(
                    severity="critical",
                    message=f"Prime Directive violation: {e}",
                    timestamp=datetime.utcnow().isoformat(),
                ))
                return KernelResult(
                    status="blocked",
                    output="Operation blocked: Violates Prime Directive",
                    operation_id=operation_id,
                    authority_required=operation.authority_level,
                    error=str(e),
                )
            except ProhibitedOperationViolation as e:
                self._metrics['operations_blocked'] += 1
                await self._broadcast_alert(Alert(
                    severity="critical",
                    message=f"Prohibited operation: {e}",
                    timestamp=datetime.utcnow().isoformat(),
                ))
                return KernelResult(
                    status="blocked",
                    output="Operation blocked: Prohibited by Constitution",
                    operation_id=operation_id,
                    authority_required=operation.authority_level,
                    error=str(e),
                )
            except ConstitutionalViolation as e:
                self._metrics['operations_rejected'] += 1
                return KernelResult(
                    status="rejected",
                    output=f"Constitutional violation: {e}",
                    operation_id=operation_id,
                    authority_required=operation.authority_level,
                    error=str(e),
                )
            
            # Check authority requirements
            requirements = get_authority_requirements(operation.authority_level)
            
            # Log to audit trail
            if self.audit_logger:
                self.audit_logger.log(
                    level="OPERATION",
                    action=operation.skill_name,
                    tool=operation.skill_name.split("_")[0],
                    parameters={"command": command, "user": user},
                    authority=str(operation.authority_level),
                    result="pending",
                    session_id=user,
                )
            
            # Check if approval is required
            if requirements.approval_needed:
                approval_id = f"apr_{uuid.uuid4().hex[:12]}"
                return KernelResult(
                    status="pending_approval",
                    output=f"Operation requires approval at {operation.authority_level.name_display}",
                    operation_id=operation_id,
                    authority_required=operation.authority_level,
                    requires_approval=True,
                    approval_id=approval_id,
                )
            
            # Execute through agent fleet
            result = await self._agent_fleet_execute(operation)
            
            if result.status == "success":
                self._metrics['operations_executed'] += 1
            else:
                self._metrics['operations_failed'] += 1
            
            return KernelResult(
                status=result.status,
                output=result.output,
                operation_id=operation_id,
                authority_required=operation.authority_level,
                error=getattr(result, 'error', None),
            )
            
        except ConstitutionalViolation as e:
            self._metrics['operations_rejected'] += 1
            await self._broadcast_alert(Alert(
                severity="critical",
                message=f"Constitutional violation: {e}",
                timestamp=datetime.utcnow().isoformat(),
            ))
            
            return KernelResult(
                status="rejected",
                output=f"Constitutional violation: {e}",
                operation_id=operation_id,
                authority_required=AuthorityLevel.READ_ONLY,
                error=str(e),
            )
            
        except Exception as e:
            self._metrics['operations_failed'] += 1
            logger.error(f"Operation failed: {e}", exc_info=True)
            
            await self._broadcast_alert(Alert(
                severity="error",
                message=f"Operation failed: {e}",
                timestamp=datetime.utcnow().isoformat(),
            ))
            
            return KernelResult(
                status="error",
                output=f"Error: {e}",
                operation_id=operation_id,
                authority_required=AuthorityLevel.READ_ONLY,
                error=str(e),
            )
    
    async def _agent_fleet_execute(self, operation: Operation) -> 'AgentResult':
        """
        Execute an operation through the agent fleet using real API calls.
        
        Args:
            operation: The operation to execute
            
        Returns:
            Result from execution with citations and confidence
        """
        try:
            # Get API client
            api_client = get_api_client()
            
            # Determine task type based on skill
            task_type = self._map_skill_to_task_type(operation.skill_name)
            
            # Build prompt with operation context
            prompt = self._build_execution_prompt(operation)
            
            # Call API with citation requirements
            llm_response = await api_client.complete(
                prompt=prompt,
                task_type=task_type,
                max_context=True
            )
            
            # Build output with citations
            output = llm_response.content
            
            # Add citation info to output if present
            if llm_response.citations:
                citation_text = "\n\n**Sources:**\n"
                for cit in llm_response.citations:
                    citation_text += f"- [{cit.file}:{cit.lines}] (relevance: {cit.relevance})\n"
                output += citation_text
            
            # Add confidence info
            output += f"\n\n**Confidence:** {llm_response.confidence:.1%}"
            
            return AgentResult(
                status="success",
                output=output,
                error=None
            )
            
        except Exception as e:
            logger.error(f"Agent fleet execution failed: {e}")
            return AgentResult(
                status="error",
                output=f"Operation failed: {str(e)}",
                error=str(e)
            )
    
    def _map_skill_to_task_type(self, skill_name: str) -> TaskType:
        """Map skill name to task type for API routing"""
        skill_lower = skill_name.lower()
        
        if "search" in skill_lower or "web" in skill_lower:
            return TaskType.REASONING
        elif "code" in skill_lower or "analyze" in skill_lower:
            return TaskType.CODING
        elif "write" in skill_lower or "create" in skill_lower:
            return TaskType.CREATIVE
        elif "math" in skill_lower or "calculate" in skill_lower:
            return TaskType.REASONING
        else:
            return TaskType.CHAT
    
    def _build_execution_prompt(self, operation: Operation) -> str:
        """Build execution prompt with operation details"""
        prompt = f"""Execute the following operation:

Operation: {operation.skill_name}
Description: {operation.description}
Parameters: {json.dumps(operation.parameters, indent=2)}

Please execute this operation and provide the results with proper citations."""

        return prompt
    
    async def _broadcast_alert(self, alert: Alert) -> None:
        """
        Broadcast an alert to all interfaces.
        
        Args:
            alert: The alert to broadcast
        """
        for interface in self.active_interfaces:
            try:
                if hasattr(interface, 'notify_alert'):
                    await interface.notify_alert(alert)
            except Exception as e:
                logger.error(f"Failed to send alert to interface: {e}")
    
    async def start_interface_loops(self) -> None:
        """Start listening on all registered interfaces."""
        self._running = True
        
        tasks = [
            self._interface_loop(interface)
            for interface in self.active_interfaces
        ]
        
        logger.info("Starting interface loops...")
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _interface_loop(self, interface: Any) -> None:
        """
        Main loop for a single interface.
        
        Args:
            interface: The interface adapter to run loop for
        """
        logger.info(f"Starting interface loop: {interface.__class__.__name__}")
        
        while self._running and not self._shutdown_requested:
            try:
                if hasattr(interface, 'receive_input'):
                    command = await asyncio.wait_for(
                        interface.receive_input(),
                        timeout=1.0,
                    )
                    
                    if command:
                        response = await self.process_command(command)
                        
                        if hasattr(interface, 'send_output'):
                            await interface.send_output(response.output)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Interface loop error: {e}", exc_info=True)
                await asyncio.sleep(1)
        
        logger.info(f"Interface loop stopped: {interface.__class__.__name__}")
    
    async def emergency_shutdown(self, mode: str = "soft") -> None:
        """
        Trigger emergency shutdown.
        
        Args:
            mode: Shutdown mode ('soft', 'hard', 'quarantine')
        """
        logger.warning(f"Emergency shutdown requested: {mode}")
        
        self._shutdown_requested = True
        
        if mode == "hard":
            logger.critical("HARD SHUTDOWN - Terminating immediately")
            self._running = False
            return
        
        if mode == "quarantine":
            logger.warning("QUARANTINE MODE - Isolating compromised agents")
            self._running = False
            return
        
        if mode == "soft":
            logger.warning("SOFT SHUTDOWN - Graceful termination")
            self._running = False
            await asyncio.sleep(30)
            return
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get kernel metrics.
        
        Returns:
            Dictionary of kernel metrics
        """
        uptime = datetime.utcnow() - self._metrics['start_time']
        
        return {
            **self._metrics,
            'uptime_seconds': uptime.total_seconds(),
            'agents_active': len(self.agent_fleet),
            'interfaces_active': len(self.active_interfaces),
        }
    
    def get_operation_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get operation history.
        
        Args:
            limit: Maximum number of operations to return
            
        Returns:
            List of operation dictionaries
        """
        history = [
            {
                'operation_id': op.operation_id,
                'skill_name': op.skill_name,
                'authority_level': op.authority_level.name,
                'description': op.description,
            }
            for op in self._operation_history.values()
        ]
        
        return history[-limit:]


class AgentResult:
    """Result from agent execution."""
    
    def __init__(self, status: str, output: str, error: str = None):
        self.status = status
        self.output = output
        self.error = error

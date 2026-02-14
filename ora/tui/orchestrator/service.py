"""Orchestrator service managing multi-agent execution."""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import uuid

from ora.orchestrator.graph import SimpleOrchestrator, AgentState


@dataclass
class PendingApproval:
    """A pending action awaiting human approval."""
    id: str
    agent: str
    operation: str
    description: str
    query: str
    state: Dict[str, Any]


class OrchestratorService:
    """
    Manages multi-agent orchestration and human-in-the-loop approvals.
    
    Usage:
        service = OrchestratorService()
        result = service.process_query("delete old files")
        
        if result["requires_approval"]:
            # Show approval panel
            approval_id = result["approval_id"]
            # ... user clicks approve ...
            service.approve(approval_id)
    """
    
    def __init__(self):
        self.orchestrator = SimpleOrchestrator()
        self.pending_approvals: Dict[str, PendingApproval] = {}
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query through the agent system.
        
        Returns dict with:
            - agent: Which specialist handled the query
            - response: Text response (if available)
            - requires_approval: Whether action needs human approval
            - approval_id: ID to use for approval (if required)
            - pending_action: Details about the pending action
        """
        result = self.orchestrator.process_query(query)
        
        if result["requires_approval"]:
            # Create pending approval
            approval_id = str(uuid.uuid4())[:8]
            
            pending = PendingApproval(
                id=approval_id,
                agent=result["agent"],
                operation=result["pending_action"].get("operation", ""),
                description=result["pending_action"].get("description", ""),
                query=query,
                state={
                    "messages": [],
                    "user_query": query,
                    "current_agent": result["agent"],
                    "specialist_response": "",
                    "requires_approval": True,
                    "approved": False,
                    "pending_action": result["pending_action"],
                },
            )
            
            self.pending_approvals[approval_id] = pending
            result["approval_id"] = approval_id
        
        return result
    
    def approve(self, approval_id: str) -> Dict[str, Any]:
        """
        Approve a pending action and execute it.
        
        Returns:
            Dict with execution result
        """
        if approval_id not in self.pending_approvals:
            return {"error": "Approval not found", "success": False}
        
        pending = self.pending_approvals.pop(approval_id)
        
        # Execute the approved action
        state: AgentState = pending.state  # type: ignore
        result_state = self.orchestrator.approve_and_execute(state)
        
        return {
            "success": True,
            "agent": pending.agent,
            "operation": pending.operation,
            "response": result_state.get("specialist_response", "Action completed"),
        }
    
    def reject(self, approval_id: str, reason: str = "") -> Dict[str, Any]:
        """
        Reject a pending action.
        
        Args:
            approval_id: The approval to reject
            reason: Optional reason for rejection (for learning)
        
        Returns:
            Dict with rejection confirmation
        """
        if approval_id not in self.pending_approvals:
            return {"error": "Approval not found", "success": False}
        
        pending = self.pending_approvals.pop(approval_id)
        
        return {
            "success": True,
            "rejected": True,
            "agent": pending.agent,
            "operation": pending.operation,
            "reason": reason,
        }
    
    def get_pending(self, approval_id: str) -> Optional[PendingApproval]:
        """Get details of a pending approval."""
        return self.pending_approvals.get(approval_id)
    
    def list_pending(self) -> list[PendingApproval]:
        """List all pending approvals."""
        return list(self.pending_approvals.values())
    
    def clear_pending(self) -> int:
        """Clear all pending approvals. Returns count cleared."""
        count = len(self.pending_approvals)
        self.pending_approvals.clear()
        return count

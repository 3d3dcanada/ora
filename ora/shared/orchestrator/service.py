"""ora.orchestrator.service - Orchestrator service managing multi-agent execution and approvals."""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from .graph import OraOrchestrator, AgentState


@dataclass
class PendingApproval:
    """A pending action awaiting human approval."""
    id: str
    agent: str
    operation: str
    description: str
    query: str
    authority_required: str
    state: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    user: str = "Randall"


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
    
    def __init__(self, orchestrator: Optional[OraOrchestrator] = None):
        """
        Initialize the orchestrator service.
        
        Args:
            orchestrator: Optional OraOrchestrator instance
        """
        self.orchestrator = orchestrator or OraOrchestrator()
        self.pending_approvals: Dict[str, PendingApproval] = {}
        self.approval_history: list = []
    
    def process_query(self, query: str, user: str = "Randall") -> Dict[str, Any]:
        """
        Process a user query through the agent system.
        
        Args:
            query: The user query
            user: The user making the request
            
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
            approval_id = f"apr_{uuid.uuid4().hex[:12]}"
            
            pending = PendingApproval(
                id=approval_id,
                agent=result["agent"],
                operation=result["pending_action"].get("operation", ""),
                description=result["pending_action"].get("description", ""),
                query=query,
                authority_required=result["pending_action"].get("authority_required", "A2"),
                state={
                    "messages": [],
                    "user_query": query,
                    "current_agent": result["agent"],
                    "specialist_response": "",
                    "requires_approval": True,
                    "approved": False,
                    "pending_action": result["pending_action"],
                },
                user=user,
            )
            
            self.pending_approvals[approval_id] = pending
            result["approval_id"] = approval_id
            result["authority_required"] = pending.authority_required
        
        return result
    
    def approve(self, approval_id: str, approver: str = "human") -> Dict[str, Any]:
        """
        Approve a pending action and execute it.
        
        Args:
            approval_id: The approval ID to approve
            approver: Who approved the action
            
        Returns:
            Dict with execution result
        """
        if approval_id not in self.pending_approvals:
            return {"error": "Approval not found", "success": False}
        
        pending = self.pending_approvals.pop(approval_id)
        
        # Execute the approved action
        state: AgentState = pending.state  # type: ignore
        result_state = self.orchestrator.approve_and_execute(state)
        
        # Record in history
        self.approval_history.append({
            "id": approval_id,
            "agent": pending.agent,
            "operation": pending.operation,
            "status": "approved",
            "approver": approver,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        return {
            "success": True,
            "approved": True,
            "agent": pending.agent,
            "operation": pending.operation,
            "response": result_state.get("specialist_response", "Action completed"),
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def reject(self, approval_id: str, reason: str = "", rejecter: str = "human") -> Dict[str, Any]:
        """
        Reject a pending action.
        
        Args:
            approval_id: The approval to reject
            reason: Optional reason for rejection (for learning)
            rejecter: Who rejected the action
            
        Returns:
            Dict with rejection confirmation
        """
        if approval_id not in self.pending_approvals:
            return {"error": "Approval not found", "success": False}
        
        pending = self.pending_approvals.pop(approval_id)
        
        # Record in history with rejection reason (for learning)
        self.approval_history.append({
            "id": approval_id,
            "agent": pending.agent,
            "operation": pending.operation,
            "status": "rejected",
            "reason": reason,
            "rejecter": rejecter,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        return {
            "success": True,
            "rejected": True,
            "agent": pending.agent,
            "operation": pending.operation,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def get_pending(self, approval_id: str) -> Optional[PendingApproval]:
        """Get details of a pending approval."""
        return self.pending_approvals.get(approval_id)
    
    def list_pending(self) -> list[PendingApproval]:
        """List all pending approvals."""
        return list(self.pending_approvals.values())
    
    def list_pending_summaries(self) -> list[Dict[str, Any]]:
        """List all pending approvals as dictionaries."""
        return [
            {
                "id": p.id,
                "agent": p.agent,
                "operation": p.operation,
                "description": p.description,
                "authority_required": p.authority_required,
                "query": p.query,
                "created_at": p.created_at,
                "user": p.user,
            }
            for p in self.pending_approvals.values()
        ]
    
    def get_approval_history(self, limit: int = 100) -> list:
        """Get approval history."""
        return self.approval_history[-limit:]
    
    def clear_pending(self) -> int:
        """Clear all pending approvals. Returns count cleared."""
        count = len(self.pending_approvals)
        self.pending_approvals.clear()
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        approved = sum(1 for h in self.approval_history if h["status"] == "approved")
        rejected = sum(1 for h in self.approval_history if h["status"] == "rejected")
        
        return {
            "pending_count": len(self.pending_approvals),
            "total_approved": approved,
            "total_rejected": rejected,
            "total_processed": len(self.approval_history),
        }

"""
OrA Backend Gateway - FastAPI + WebSocket Server
Main entry point for Phase 1 + Phase 2 implementation
"""

import asyncio
import json
import uuid
from typing import Optional, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging

from .config import config
from .security.vault import OraVault
from .security.authority_kernel import AuthorityKernel, AuthorityLevel
from .security.gates import SecurityGateCoordinator
from .router.smart_router import OraRouter, TaskType
from .audit.immutable_log import ImmutableAuditLog
from .core.constitution import Constitution, Operation
from .core.kernel import OraKernel, KernelResult
from .orchestrator.service import OrchestratorService, PendingApproval
from .gateway.moneymodz import MoneyModZEnforcer

logger = logging.getLogger(__name__)

# Initialize components
app = FastAPI(title="OrA Backend", version="0.2.0")
vault = OraVault()
authority_kernel = AuthorityKernel()
security_gates = SecurityGateCoordinator(str(config.workspace_root))
router = OraRouter()
audit_log = ImmutableAuditLog()

# Initialize Phase 2 components
constitution = Constitution()
kernel = OraKernel(
    constitution=constitution,
    audit_logger=audit_log,
    authority_kernel=authority_kernel,
    security_gates=security_gates,
)
orchestrator_service = OrchestratorService()

# Initialize Phase 6: MoneyModZ
moneymodz_enforcer = MoneyModZEnforcer(audit_log, constitution)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_message(self, client_id: str, message: Dict):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast_approval_request(self, approval: Dict[str, Any]):
        """Broadcast approval request to all connected clients."""
        message = {
            "type": "approval_request",
            "id": approval.get("id", ""),
            "agent": approval.get("agent", ""),
            "operation": approval.get("operation", ""),
            "description": approval.get("description", ""),
            "authority_required": approval.get("authority_required", "A2"),
            "query": approval.get("query", ""),
            "created_at": approval.get("created_at", ""),
        }
        for client_id in list(self.active_connections.keys()):
            try:
                await self.send_message(client_id, message)
            except Exception:
                pass  # Client may have disconnected
    
    async def broadcast_approval_update(self, approval_id: str, approved: bool, reason: str = ""):
        """Broadcast approval result to all connected clients."""
        message = {
            "type": "approval_update",
            "approval_id": approval_id,
            "approved": approved,
            "reason": reason,
        }
        for client_id in list(self.active_connections.keys()):
            try:
                await self.send_message(client_id, message)
            except Exception:
                pass  # Client may have disconnected
    
    async def broadcast_moneymodz_update(self, active: bool):
        """Broadcast MoneyModZ mode update to all connected clients."""
        message = {
            "type": "moneymodz_update",
            "active": active,
            "timestamp": "2026-02-08T19:00:00Z",
        }
        for client_id in list(self.active_connections.keys()):
            try:
                await self.send_message(client_id, message)
            except Exception:
                pass  # Client may have disconnected

manager = ConnectionManager()


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "OrA Backend API", "version": "0.2.0", "phase": 2}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok", 
        "timestamp": "2026-02-08T19:00:00Z",
        "phase": 2,
        "components": {
            "vault": vault.is_unlocked() if hasattr(vault, 'is_unlocked') else "unknown",
            "constitution": constitution.verify_immutability(),
            "kernel": "running",
        }
    }


@app.get("/config")
async def get_config():
    """Get current configuration"""
    return {
        "host": config.host,
        "port": config.port,
        "ws_port": config.ws_port,
        "workspace_root": str(config.workspace_root),
        "default_model": config.default_model,
        "max_authority_level": config.max_authority_level,
        "user_name": config.user_name
    }


# Constitution endpoints
@app.get("/constitution")
async def get_constitution():
    """Get constitution summary"""
    return {
        "version": constitution.version,
        "prime_directive": constitution.prime_directive,
        "prohibited_operations": constitution.PROHIBITED_OPERATIONS,
        "authority_hierarchy": constitution.AUTHORITY_HIERARCHY,
    }


@app.post("/constitution/verify")
async def verify_constitution():
    """Verify constitution immutability"""
    return {
        "valid": constitution.verify_immutability(),
        "hash": constitution._immutable_hash,
    }


# Kernel endpoints
@app.get("/kernel/metrics")
async def get_kernel_metrics():
    """Get kernel metrics"""
    return kernel.get_metrics()


@app.get("/kernel/history")
async def get_operation_history(limit: int = 100):
    """Get operation history"""
    return {"operations": kernel.get_operation_history(limit)}


@app.post("/kernel/process")
async def process_command(command: str, user: str = "Randall"):
    """
    Process a command through the kernel.
    
    This is the main command processing endpoint that:
    1. Parses the command into an operation
    2. Validates against constitution
    3. Checks authority requirements
    4. Returns result with approval info if needed
    """
    try:
        result = await kernel.process_command(command, user)
        
        # If approval is required, create pending approval
        if result.requires_approval:
            pending = PendingApproval(
                id=result.approval_id,
                agent="kernel",
                operation=result.output,
                description=f"Command: {command[:100]}",
                query=command,
                authority_required=str(result.authority_required.name_display),
            )
            orchestrator_service.pending_approvals[result.approval_id] = pending
            
            # Broadcast to WebSocket clients
            await manager.broadcast_approval_request({
                "id": result.approval_id,
                "agent": "kernel",
                "operation": result.output,
                "description": pending.description,
                "authority_required": pending.authority_required,
                "query": command,
                "created_at": pending.created_at,
            })
        
        return {
            "status": result.status,
            "output": result.output,
            "operation_id": result.operation_id,
            "authority_required": str(result.authority_required),
            "requires_approval": result.requires_approval,
            "approval_id": result.approval_id,
            "error": result.error,
        }
        
    except Exception as e:
        logger.error(f"Command processing failed: {e}")
        return {"status": "error", "output": str(e), "error": str(e)}


# Orchestrator endpoints
@app.post("/orchestrator/query")
async def process_orchestrator_query(query: str, user: str = "Randall"):
    """Process a query through the orchestrator."""
    try:
        result = orchestrator_service.process_query(query, user)
        
        # If approval is required, broadcast to WebSocket clients
        if result.get("requires_approval"):
            await manager.broadcast_approval_request({
                "id": result.get("approval_id"),
                "agent": result.get("agent"),
                "operation": result.get("pending_action", {}).get("operation", ""),
                "description": result.get("pending_action", {}).get("description", ""),
                "authority_required": result.get("authority_required", "A2"),
                "query": query,
                "created_at": "2026-02-08T19:00:00Z",
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Orchestrator query failed: {e}")
        return {"error": str(e)}


# Approval endpoints
@app.get("/approvals")
async def list_approvals():
    """List all pending approvals"""
    return {"approvals": orchestrator_service.list_pending_summaries()}


@app.get("/approvals/stats")
async def get_approval_stats():
    """Get approval statistics"""
    return orchestrator_service.get_stats()


@app.post("/approvals/{approval_id}/approve")
async def approve_action(approval_id: str, approver: str = "human"):
    """Approve a pending action"""
    try:
        result = orchestrator_service.approve(approval_id, approver)
        
        if result.get("success"):
            # Broadcast approval to WebSocket clients
            await manager.broadcast_approval_update(approval_id, True)
        
        return result
        
    except Exception as e:
        logger.error(f"Approval failed: {e}")
        return {"error": str(e), "success": False}


@app.post("/approvals/{approval_id}/reject")
async def reject_action(approval_id: str, reason: str = "", rejecter: str = "human"):
    """Reject a pending action"""
    try:
        result = orchestrator_service.reject(approval_id, reason, rejecter)
        
        if result.get("success"):
            # Broadcast rejection to WebSocket clients
            await manager.broadcast_approval_update(approval_id, False, reason)
        
        return result
        
    except Exception as e:
        logger.error(f"Rejection failed: {e}")
        return {"error": str(e), "success": False}


@app.delete("/approvals")
async def clear_approvals():
    """Clear all pending approvals"""
    count = orchestrator_service.clear_pending()
    return {"cleared": count}


# Vault endpoints
@app.post("/vault/create")
async def create_vault(password: Optional[str] = None):
    """Create new encrypted vault"""
    try:
        success = vault.create(password)
        if success:
            audit_log.log(
                level="SECURITY",
                action="vault_created",
                tool="vault",
                authority="A4",
                result="success"
            )
            return {"success": True, "message": "Vault created successfully"}
        else:
            return {"success": False, "error": "Failed to create vault"}
    except Exception as e:
        logger.error(f"Vault creation failed: {e}")
        return {"success": False, "error": str(e)}


@app.post("/vault/unlock")
async def unlock_vault(password: Optional[str] = None):
    """Unlock the vault"""
    try:
        success = vault.unlock(password)
        if success:
            audit_log.log(
                level="SECURITY",
                action="vault_unlocked",
                tool="vault",
                authority="A4",
                result="success"
            )
            return {"success": True, "message": "Vault unlocked successfully"}
        else:
            return {"success": False, "error": "Failed to unlock vault"}
    except Exception as e:
        logger.error(f"Vault unlock failed: {e}")
        return {"success": False, "error": str(e)}


@app.post("/vault/lock")
async def lock_vault():
    """Lock the vault"""
    try:
        vault.lock()
        audit_log.log(
            level="SECURITY",
            action="vault_locked",
            tool="vault",
            authority="A4",
            result="success"
        )
        return {"success": True, "message": "Vault locked successfully"}
    except Exception as e:
        logger.error(f"Vault lock failed: {e}")
        return {"success": False, "error": str(e)}


# Authority endpoints
@app.get("/authority/current")
async def get_current_authority():
    """Get current authority level"""
    current = authority_kernel.get_current_authority()
    return {
        "authority_level": str(current),
        "numeric_level": current.value,
        "description": "A0-Guest: Read-only, no network" if current == AuthorityLevel.GUEST else
                      "A1-User: Read-write workspace, limited network" if current == AuthorityLevel.USER else
                      "A2-Developer: Sandboxed shell, full network" if current == AuthorityLevel.DEVELOPER else
                      "A3-Senior: Unsandboxed shell (with approval)" if current == AuthorityLevel.SENIOR else
                      "A4-Admin: System-wide access, credential modification" if current == AuthorityLevel.ADMIN else
                      "A5-Root: Disable gates temporarily (requires 2FA/hardware key)"
    }


@app.post("/authority/escalate")
async def escalate_authority(
    new_level: int,
    reason: str,
    auth_code: Optional[str] = None,
    session_id: Optional[str] = None
):
    """Request authority escalation"""
    try:
        if new_level < 0 or new_level > 5:
            raise HTTPException(status_code=400, detail="Authority level must be 0-5")
        
        result = authority_kernel.escalate(
            AuthorityLevel(new_level),
            reason,
            auth_code,
            session_id
        )
        return result
    except Exception as e:
        logger.error(f"Authority escalation failed: {e}")
        return {"success": False, "error": str(e)}


# Router endpoints
@app.post("/router/analyze")
async def analyze_task(prompt: str):
    """Analyze prompt and determine task type"""
    try:
        task_type = router.analyze_task(prompt)
        return {
            "task_type": task_type.value,
            "description": {
                TaskType.REASONING: "Deep logic, math, complex analysis",
                TaskType.CODING: "Code generation, debugging",
                TaskType.CREATIVE: "Writing, explanations",
                TaskType.STRUCTURED: "JSON, schemas, strict formatting",
                TaskType.CHAT: "General conversation",
                TaskType.LONG_CONTEXT: "Document analysis, large inputs"
            }[task_type]
        }
    except Exception as e:
        logger.error(f"Task analysis failed: {e}")
        return {"error": str(e)}


@app.post("/router/select")
async def select_model(
    prompt: str,
    preferred_provider: Optional[str] = None,
    force_model: Optional[str] = None
):
    """Select appropriate model for task"""
    try:
        result = router.route_request(prompt, force_model, preferred_provider)
        return result
    except Exception as e:
        logger.error(f"Model selection failed: {e}")
        return {"error": str(e)}


# Security endpoints
@app.post("/security/check")
async def security_check(request: Dict[str, Any]):
    """Run security gates on request"""
    try:
        result = security_gates.run_all_gates(request)
        return result
    except Exception as e:
        logger.error(f"Security check failed: {e}")
        return {"error": str(e)}


# Audit endpoints
@app.get("/audit/verify")
async def verify_audit_chain(limit: int = 1000):
    """Verify integrity of audit chain"""
    try:
        result = audit_log.verify_chain(limit)
        return result
    except Exception as e:
        logger.error(f"Audit verification failed: {e}")
        return {"error": str(e)}


@app.get("/audit/query")
async def query_audit_log(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    level: Optional[str] = None,
    tool: Optional[str] = None,
    limit: int = 100
):
    """Query audit log entries"""
    try:
        entries = audit_log.query(start_time, end_time, level, tool, limit)
        return {"entries": entries, "count": len(entries)}
    except Exception as e:
        logger.error(f"Audit query failed: {e}")
        return {"error": str(e)}


# MoneyModZ endpoints
@app.get("/moneymodz/status")
async def get_moneymodz_status():
    """Get MoneyModZ mode status"""
    return {
        "enabled": moneymodz_enforcer.moneymodz_enabled,
        "active": moneymodz_enforcer.active,
        "allowed_tools": list(moneymodz_enforcer.allowed_tools),
        "confidence_threshold": 0.95,
        "audit_log_path": str(moneymodz_enforcer.moneymodz_audit_log)
    }


@app.post("/moneymodz/toggle")
async def toggle_moneymodz(active: bool):
    """Toggle MoneyModZ mode on/off"""
    try:
        moneymodz_enforcer.set_active(active)
        return {
            "success": True,
            "active": moneymodz_enforcer.active,
            "message": f"MoneyModZ mode {'activated' if active else 'deactivated'}"
        }
    except Exception as e:
        logger.error(f"MoneyModZ toggle failed: {e}")
        return {"success": False, "error": str(e)}


@app.post("/moneymodz/enforce")
async def enforce_moneymodz(request: Dict[str, Any]):
    """Apply MoneyModZ constraints to a request"""
    try:
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        result = moneymodz_enforcer.enforce_moneymodz_constraints(
            request, session_id, "gateway"
        )
        return {
            "success": True,
            "modified_request": result,
            "session_id": session_id,
            "in_moneymodz_mode": moneymodz_enforcer.is_moneymodz_mode(request.get("metadata"))
        }
    except Exception as e:
        logger.error(f"MoneyModZ enforcement failed: {e}")
        return {"success": False, "error": str(e)}


@app.get("/moneymodz/audit")
async def get_moneymodz_audit(limit: int = 100):
    """Get MoneyModZ audit log entries"""
    try:
        if moneymodz_enforcer.moneymodz_audit_log.exists():
            entries = []
            with open(moneymodz_enforcer.moneymodz_audit_log, "r") as f:
                for i, line in enumerate(f):
                    if i >= limit:
                        break
                    entries.append(json.loads(line.strip()))
            return {"entries": entries, "count": len(entries)}
        else:
            return {"entries": [], "count": 0}
    except Exception as e:
        logger.error(f"MoneyModZ audit query failed: {e}")
        return {"error": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str = "default"):
    """WebSocket endpoint for real-time communication"""
    await manager.connect(websocket, client_id)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "timestamp": "2026-02-08T19:00:00Z",
            "pending_approvals": orchestrator_service.list_pending_summaries(),
        })
        
        while True:
            data = await websocket.receive_json()
            
            # Log the incoming message
            audit_log.log(
                level="WEBSOCKET",
                action="message_received",
                tool="websocket",
                parameters={"client_id": client_id, "data_type": type(data).__name__},
                authority=str(authority_kernel.get_current_authority()),
                result="received",
                session_id=client_id
            )
            
            # Process message based on type
            message_type = data.get("type", "unknown")
            
            if message_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": "2026-02-08T19:00:00Z"})
            
            elif message_type == "chat":
                # Process chat command through kernel
                command = data.get("message", "")
                result = await kernel.process_command(command, client_id)
                
                await websocket.send_json({
                    "type": "chat_response",
                    "message": result.output,
                    "status": result.status,
                    "operation_id": result.operation_id,
                    "requires_approval": result.requires_approval,
                    "approval_id": result.approval_id,
                    "timestamp": "2026-02-08T19:00:00Z"
                })
                
                # If approval required, broadcast to all clients
                if result.requires_approval:
                    pending = PendingApproval(
                        id=result.approval_id,
                        agent="kernel",
                        operation=result.output,
                        description=f"Command: {command[:100]}",
                        query=command,
                        authority_required=str(result.authority_required.name_display),
                    )
                    orchestrator_service.pending_approvals[result.approval_id] = pending
                    await manager.broadcast_approval_request({
                        "id": result.approval_id,
                        "agent": "kernel",
                        "operation": result.output,
                        "description": pending.description,
                        "authority_required": pending.authority_required,
                        "query": command,
                        "created_at": pending.created_at,
                    })
            
            elif message_type == "approval_response":
                # Handle approval response from frontend
                approval_id = data.get("id")
                approved = data.get("approved", False)
                reason = data.get("reason", "")
                
                if approved:
                    result = orchestrator_service.approve(approval_id, client_id)
                else:
                    result = orchestrator_service.reject(approval_id, reason, client_id)
                
                await websocket.send_json({
                    "type": "approval_result",
                    "id": approval_id,
                    "approved": approved,
                    "result": result,
                    "timestamp": "2026-02-08T19:00:00Z"
                })
                
                # Broadcast update to all clients
                await manager.broadcast_approval_update(approval_id, approved, reason)
            
            elif message_type == "query":
                # Process through orchestrator
                query = data.get("query", "")
                result = orchestrator_service.process_query(query, client_id)
                
                await websocket.send_json({
                    "type": "query_response",
                    "result": result,
                    "timestamp": "2026-02-08T19:00:00Z"
                })
                
                # If approval required, broadcast
                if result.get("requires_approval"):
                    await manager.broadcast_approval_request({
                        "id": result.get("approval_id"),
                        "agent": result.get("agent"),
                        "operation": result.get("pending_action", {}).get("operation", ""),
                        "description": result.get("pending_action", {}).get("description", ""),
                        "authority_required": result.get("authority_required", "A2"),
                        "query": query,
                        "created_at": "2026-02-08T19:00:00Z",
                    })
            
            elif message_type == "get_pending":
                # Send current pending approvals
                await websocket.send_json({
                    "type": "pending_approvals",
                    "approvals": orchestrator_service.list_pending_summaries(),
                    "timestamp": "2026-02-08T19:00:00Z"
                })
            
            elif message_type == "moneymodz_toggle":
                # Toggle MoneyModZ mode
                active = data.get("active", False)
                moneymodz_enforcer.set_active(active)
                
                # Broadcast to all clients
                await manager.broadcast_moneymodz_update(active)
                
                await websocket.send_json({
                    "type": "moneymodz_status",
                    "active": moneymodz_enforcer.active,
                    "message": f"MoneyModZ mode {'activated' if active else 'deactivated'}",
                    "timestamp": "2026-02-08T19:00:00Z"
                })
            
            elif message_type == "moneymodz_status":
                # Get MoneyModZ status
                await websocket.send_json({
                    "type": "moneymodz_status",
                    "active": moneymodz_enforcer.active,
                    "enabled": moneymodz_enforcer.moneymodz_enabled,
                    "allowed_tools": list(moneymodz_enforcer.allowed_tools),
                    "timestamp": "2026-02-08T19:00:00Z"
                })
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(client_id)


def main():
    """Main entry point"""
    uvicorn.run(
        "ora.main:app",
        host=config.host,
        port=config.port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()

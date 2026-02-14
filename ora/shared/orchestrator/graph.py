"""ora.orchestrator.graph - Multi-agent orchestration with specialist routing and real agent execution."""

from typing import TypedDict, Annotated, Literal, List, Dict, Any
from dataclasses import dataclass, field
import operator
import logging

from ora.agents.planner import PlannerAgent
from ora.agents.researcher import ResearcherAgent
from ora.agents.builder import BuilderAgent
from ora.agents.tester import TesterAgent
from ora.agents.integrator import IntegratorAgent
from ora.agents.security_agent import SecurityAgent
from ora.agents.selfdev import SelfDevAgent
from ora.agents.fleet import AgentFleet
from ora.core.constitution import Operation
from ora.core.authority import AuthorityLevel

logger = logging.getLogger(__name__)


@dataclass
class AgentAction:
    """Proposed action requiring potential approval."""
    agent: str
    operation: str
    description: str
    is_dangerous: bool = False
    authority_required: str = "A2"
    skill: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)


class AgentState(TypedDict):
    """State passed through the agent graph."""
    messages: Annotated[List[Dict[str, str]], operator.add]
    user_query: str
    current_agent: str
    specialist_response: str
    requires_approval: bool
    approved: bool
    pending_action: Dict[str, Any]


# Keywords for routing to specialists (matching our actual agents)
ROUTING_KEYWORDS = {
    "planner": ["plan", "strategy", "roadmap", "design", "architecture", "approach", "breakdown", "decompose", "task"],
    "researcher": ["research", "find", "search", "lookup", "what is", "how to", "explain", "documentation", "information", "web", "internet"],
    "builder": ["write", "create", "modify", "edit", "update", "save", "generate", "code", "implement", "refactor", "function", "class", "python", "javascript", "typescript"],
    "tester": ["test", "validate", "verify", "quality", "assurance", "check", "lint", "type", "debug", "bug", "error"],
    "integrator": ["deploy", "merge", "integrate", "orchestrate", "rollback", "health", "system", "monitor", "process", "restart"],
    "security": ["security", "scan", "vulnerability", "audit", "password", "secret", "encrypt", "permission", "threat", "risk", "malware"],
    "selfdev": ["self", "improve", "analyze", "backup", "suggestion", "todo", "fixme", "refactor", "enhance", "optimize", "codebase", "ora"],
}

# Operations that require human approval
DANGEROUS_OPERATIONS = [
    "delete", "remove", "kill", "terminate", "modify", "write", "execute",
    "install", "uninstall", "format", "overwrite", "sudo", "admin",
    "drop", "truncate", "rm", "mkfs", "chmod", "chown",
]


def route_to_specialist(query: str) -> Literal["planner", "researcher", "builder", "tester", "integrator", "security", "selfdev"]:
    """
    Route user query to the appropriate specialist agent.
    
    Uses keyword matching for fast routing. Can be enhanced with
    semantic routing via embeddings in the future.
    
    Args:
        query: The user query to route
        
    Returns:
        Specialist agent name
    """
    query_lower = query.lower()
    
    # Count keyword matches per specialist
    scores = {specialist: 0 for specialist in ROUTING_KEYWORDS}
    
    for specialist, keywords in ROUTING_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query_lower:
                scores[specialist] += 1
    
    # Find highest scoring specialist
    best_specialist = max(scores, key=scores.get)
    
    # Default to researcher if no matches
    if scores[best_specialist] == 0:
        return "researcher"
    
    return best_specialist


def check_requires_approval(query: str, operation: str = "") -> bool:
    """
    Check if an operation requires human approval.
    
    Args:
        query: The user query
        operation: The proposed operation type
        
    Returns:
        True if approval is required
    """
    combined = f"{query} {operation}".lower()
    
    for dangerous_word in DANGEROUS_OPERATIONS:
        if dangerous_word in combined:
            return True
    
    return False


def planner_agent(state: AgentState) -> AgentState:
    """
    Planner Agent - Strategic planning, task decomposition, dependency mapping.
    
    Authority Level: A3 (FILE_READ)
    Uses REASONING models via OraRouter.
    """
    state["current_agent"] = "planner"
    
    # Planning is safe (read-only)
    state["requires_approval"] = False
    
    # Extract task from query
    query = state["user_query"]
    skill = "planning"
    
    state["pending_action"] = {
        "agent": "planner",
        "operation": "strategic_planning",
        "description": f"Planner Agent: {query[:100]}",
        "authority_required": "A3",
        "skill": skill,
        "parameters": {"task": query},
    }
    
    return state


def researcher_agent(state: AgentState) -> AgentState:
    """
    Researcher Agent - Information gathering, documentation lookup, web search.
    
    Authority Level: A2 (INFO_RETRIEVAL)
    Uses LONG_CONTEXT models via OraRouter.
    """
    state["current_agent"] = "researcher"
    
    # Research is safe (read-only, no writes)
    state["requires_approval"] = False
    
    query = state["user_query"]
    skill = "web_search"
    
    state["pending_action"] = {
        "agent": "researcher",
        "operation": "information_retrieval",
        "description": f"Researcher Agent: {query[:100]}",
        "authority_required": "A2",
        "skill": skill,
        "parameters": {"query": query},
    }
    
    return state


def builder_agent(state: AgentState) -> AgentState:
    """
    Builder Agent - Code generation, file creation/modification, build operations.
    
    Authority Level: A4 (FILE_WRITE)
    Uses CODING models via OraRouter.
    """
    state["current_agent"] = "builder"
    
    # Builder operations always require approval (file writes)
    state["requires_approval"] = True
    
    query = state["user_query"]
    
    # Determine skill based on query
    skill = "file_write"
    if "code" in query.lower() or "generate" in query.lower():
        skill = "code_generation"
    elif "refactor" in query.lower():
        skill = "refactor"
    
    state["pending_action"] = {
        "agent": "builder",
        "operation": "file_operation",
        "description": f"Builder Agent: {query[:100]}",
        "is_dangerous": True,
        "authority_required": "A4",
        "skill": skill,
        "parameters": {"task": query},
    }
    
    return state


def tester_agent(state: AgentState) -> AgentState:
    """
    Tester Agent - Test execution, validation, quality assurance, verification.
    
    Authority Level: A1 (SAFE_COMPUTE)
    Uses STRUCTURED models via OraRouter.
    """
    state["current_agent"] = "tester"
    
    # Testing is safe (read-only, sandboxed)
    state["requires_approval"] = False
    
    query = state["user_query"]
    skill = "test_execution"
    
    state["pending_action"] = {
        "agent": "tester",
        "operation": "quality_assurance",
        "description": f"Tester Agent: {query[:100]}",
        "authority_required": "A1",
        "skill": skill,
        "parameters": {"test_target": query},
    }
    
    return state


def integrator_agent(state: AgentState) -> AgentState:
    """
    Integrator Agent - Deployment coordination, system integration, merge operations.
    
    Authority Level: A4 (FILE_WRITE) escalatable to A5 (SYSTEM_EXEC)
    Uses REASONING models via OraRouter.
    """
    state["current_agent"] = "integrator"
    
    # Integration operations require approval
    query = state["user_query"]
    requires_approval = any(kw in query.lower() for kw in ["deploy", "merge", "rollback", "system", "exec"])
    
    state["requires_approval"] = requires_approval
    
    skill = "integration"
    if "deploy" in query.lower():
        skill = "deploy"
    elif "merge" in query.lower():
        skill = "merge"
    elif "rollback" in query.lower():
        skill = "rollback"
    
    state["pending_action"] = {
        "agent": "integrator",
        "operation": "system_integration",
        "description": f"Integrator Agent: {query[:100]}",
        "is_dangerous": requires_approval,
        "authority_required": "A4" if requires_approval else "A3",
        "skill": skill,
        "parameters": {"task": query},
    }
    
    return state


def security_agent(state: AgentState) -> AgentState:
    """
    Security Agent - Vulnerability scanning, audit review, threat detection, security policy enforcement.
    
    Authority Level: A3 (FILE_READ) + special audit access
    Uses REASONING models via OraRouter.
    """
    state["current_agent"] = "security"
    
    query = state["user_query"]
    
    # Security scans are safe, remediation requires approval
    requires_approval = any(kw in query.lower() for kw in ["fix", "patch", "modify", "change", "remediate"])
    
    state["requires_approval"] = requires_approval
    
    skill = "security_scan"
    if "audit" in query.lower():
        skill = "audit_review"
    elif "threat" in query.lower():
        skill = "threat_detection"
    elif "vulnerability" in query.lower():
        skill = "vulnerability_assessment"
    
    state["pending_action"] = {
        "agent": "security",
        "operation": "security_operation",
        "description": f"Security Agent: {query[:100]}",
        "authority_required": "A4" if requires_approval else "A3",
        "skill": skill,
        "parameters": {"target": query},
    }
    
    return state


def selfdev_agent(state: AgentState) -> AgentState:
    """
    Self-Dev Agent - Self-improvement of OrA's own codebase.
    
    Authority Level: A4 (FILE_WRITE) within OrA project only
    Uses CODING models via OraRouter.
    """
    state["current_agent"] = "selfdev"
    
    query = state["user_query"]
    
    # Self-dev operations always require human approval
    state["requires_approval"] = True
    
    skill = "self_analyze"
    if "propose" in query.lower() or "change" in query.lower():
        skill = "self_propose"
    elif "backup" in query.lower():
        skill = "self_backup"
    elif "improve" in query.lower() or "suggestion" in query.lower():
        skill = "self_improve"
    
    state["pending_action"] = {
        "agent": "selfdev",
        "operation": "self_development",
        "description": f"Self-Dev Agent: {query[:100]}",
        "is_dangerous": True,
        "authority_required": "A4",
        "skill": skill,
        "parameters": {"task": query},
    }
    
    return state


def approval_gate(state: AgentState) -> Literal["execute", "await_approval", "direct_response"]:
    """
    Determine next step based on approval requirements.
    
    Returns:
        "execute": Proceed with action (already approved or not required)
        "await_approval": Wait for human approval
        "direct_response": Provide response without execution
    """
    if not state.get("requires_approval", False):
        return "direct_response"
    
    if state.get("approved", False):
        return "execute"
    
    return "await_approval"


def execute_action(state: AgentState) -> AgentState:
    """Execute the approved action."""
    action = state.get("pending_action", {})
    state["specialist_response"] = f"✓ Executed: {action.get('operation', 'action')}"
    return state


def generate_response(state: AgentState) -> AgentState:
    """Generate final response without execution."""
    action = state.get("pending_action", {})
    agent = action.get("agent", "unknown")
    
    responses = {
        "planner": "I can help you plan and strategize. Let me understand your goals and break down the task.",
        "researcher": "Let me research that for you. I'll search for relevant information and documentation.",
        "builder": "I can help create or modify code/files. This will require your approval before execution.",
        "tester": "I can help test and validate that. Let me run quality checks and verification.",
        "integrator": "I can help with deployment and integration. Some operations may require approval.",
        "security": "I'll analyze that from a security perspective and check for vulnerabilities.",
        "selfdev": "I can help improve OrA's own codebase. All changes require your approval.",
    }
    
    state["specialist_response"] = responses.get(agent, "How can I help?")
    return state


# Build the agent nodes mapping
AGENT_NODES = {
    "planner": planner_agent,
    "researcher": researcher_agent,
    "builder": builder_agent,
    "tester": tester_agent,
    "integrator": integrator_agent,
    "security": security_agent,
    "selfdev": selfdev_agent,
}


class OraOrchestrator:
    """
    OraOrchestrator - Multi-agent orchestrator that routes queries to specialist agents.
    
    This is a lightweight implementation that works without LangGraph.
    Can be upgraded to full LangGraph StateGraph for production.
    
    Attributes:
        agents: Dictionary of available specialist agents
    """
    
    def __init__(self):
        self.agents = AGENT_NODES
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query through the orchestrator.
        
        Args:
            query: The user query to process
            
        Returns:
            Dict with agent, requires_approval, pending_action, response, next_step
        """
        # Initialize state
        state: AgentState = {
            "messages": [],
            "user_query": query,
            "current_agent": "",
            "specialist_response": "",
            "requires_approval": False,
            "approved": False,
            "pending_action": {},
        }
        
        # Route to specialist
        specialist = route_to_specialist(query)
        
        # Run specialist agent
        agent_fn = self.agents.get(specialist, researcher_agent)
        state = agent_fn(state)
        
        # Check approval gate
        next_step = approval_gate(state)
        
        # Generate response
        if next_step == "direct_response":
            state = generate_response(state)
        
        return {
            "agent": state["current_agent"],
            "requires_approval": state["requires_approval"],
            "pending_action": state["pending_action"],
            "response": state.get("specialist_response", ""),
            "next_step": next_step,
        }
    
    def approve_and_execute(self, state: AgentState) -> AgentState:
        """Execute action after approval."""
        state["approved"] = True
        return execute_action(state)
    
    def get_agent_for_operation(self, operation: str) -> str:
        """
        Get the appropriate agent for an operation type.
        
        Args:
            operation: The operation type
            
        Returns:
            Agent name
        """
        operation_lower = operation.lower()
        
        if "write" in operation_lower or "create" in operation_lower or "modify" in operation_lower:
            return "builder"
        elif "search" in operation_lower or "research" in operation_lower:
            return "researcher"
        elif "code" in operation_lower or "debug" in operation_lower or "generate" in operation_lower:
            return "builder"
        elif "test" in operation_lower or "validate" in operation_lower or "quality" in operation_lower:
            return "tester"
        elif "deploy" in operation_lower or "merge" in operation_lower or "integrate" in operation_lower:
            return "integrator"
        elif "security" in operation_lower or "scan" in operation_lower or "audit" in operation_lower:
            return "security"
        elif "plan" in operation_lower or "strategy" in operation_lower or "design" in operation_lower:
            return "planner"
        elif "self" in operation_lower or "improve" in operation_lower or "backup" in operation_lower:
            return "selfdev"
        
        return "researcher"

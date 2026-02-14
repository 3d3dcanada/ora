"""LangGraph multi-agent orchestration with specialist routing."""

from typing import TypedDict, Annotated, Literal, List, Dict, Any
from dataclasses import dataclass, field
import operator


@dataclass
class AgentAction:
    """Proposed action requiring potential approval."""
    agent: str
    operation: str
    description: str
    is_dangerous: bool = False


class AgentState(TypedDict):
    """State passed through the agent graph."""
    messages: Annotated[List[Dict[str, str]], operator.add]
    user_query: str
    current_agent: str
    specialist_response: str
    requires_approval: bool
    approved: bool
    pending_action: Dict[str, Any]


# Keywords for routing to specialists
ROUTING_KEYWORDS = {
    "code": ["code", "debug", "implement", "refactor", "function", "class", "bug", "error", "python", "javascript"],
    "research": ["research", "find", "search", "lookup", "what is", "how to", "explain", "documentation"],
    "system": ["system", "monitor", "process", "kill", "restart", "file", "folder", "directory", "delete", "move", "copy"],
    "security": ["security", "scan", "vulnerability", "audit", "password", "secret", "encrypt", "permission"],
}

# Operations that require human approval
DANGEROUS_OPERATIONS = [
    "delete", "remove", "kill", "terminate", "modify", "write", "execute",
    "install", "uninstall", "format", "overwrite", "sudo", "admin",
]


def route_to_specialist(state: AgentState) -> Literal["code", "research", "system", "security"]:
    """
    Route user query to the appropriate specialist agent.
    
    Uses keyword matching for fast routing. Can be enhanced with
    semantic routing via embeddings in the future.
    """
    query = state["user_query"].lower()
    
    # Count keyword matches per specialist
    scores = {specialist: 0 for specialist in ROUTING_KEYWORDS}
    
    for specialist, keywords in ROUTING_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query:
                scores[specialist] += 1
    
    # Find highest scoring specialist
    best_specialist = max(scores, key=scores.get)
    
    # Default to research if no matches
    if scores[best_specialist] == 0:
        return "research"
    
    return best_specialist


def check_requires_approval(query: str, operation: str) -> bool:
    """Check if an operation requires human approval."""
    combined = f"{query} {operation}".lower()
    
    for dangerous_word in DANGEROUS_OPERATIONS:
        if dangerous_word in combined:
            return True
    
    return False


def code_agent(state: AgentState) -> AgentState:
    """
    Code specialist agent.
    
    Handles: code analysis, generation, debugging, refactoring
    """
    state["current_agent"] = "code"
    
    # Determine if operation is dangerous
    operation = "analyze code"  # Default
    if any(kw in state["user_query"].lower() for kw in ["write", "modify", "refactor", "fix"]):
        operation = "modify code"
        state["requires_approval"] = True
    else:
        state["requires_approval"] = False
    
    state["pending_action"] = {
        "agent": "code",
        "operation": operation,
        "description": f"Code Agent analyzing: {state['user_query'][:100]}",
    }
    
    return state


def research_agent(state: AgentState) -> AgentState:
    """
    Research specialist agent.
    
    Handles: web search, documentation lookup, knowledge retrieval
    """
    state["current_agent"] = "research"
    state["requires_approval"] = False  # Research is safe
    
    state["pending_action"] = {
        "agent": "research",
        "operation": "search and retrieve",
        "description": f"Research Agent looking up: {state['user_query'][:100]}",
    }
    
    return state


def system_agent(state: AgentState) -> AgentState:
    """
    System operations agent.
    
    Handles: process management, file operations, system monitoring
    """
    state["current_agent"] = "system"
    
    # System operations often require approval
    operation = "system operation"
    requires_approval = check_requires_approval(state["user_query"], operation)
    
    state["requires_approval"] = requires_approval
    state["pending_action"] = {
        "agent": "system",
        "operation": operation,
        "description": f"System Agent preparing: {state['user_query'][:100]}",
        "is_dangerous": requires_approval,
    }
    
    return state


def security_agent(state: AgentState) -> AgentState:
    """
    Security specialist agent.
    
    Handles: vulnerability scanning, security audits, threat detection
    """
    state["current_agent"] = "security"
    
    # Security scans are generally safe, modifications are not
    operation = "security scan"
    requires_approval = any(kw in state["user_query"].lower() for kw in ["fix", "patch", "modify", "change"])
    
    state["requires_approval"] = requires_approval
    state["pending_action"] = {
        "agent": "security",
        "operation": operation,
        "description": f"Security Agent analyzing: {state['user_query'][:100]}",
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
        "code": "I can help with that code task. What would you like me to analyze or modify?",
        "research": "Let me look that up for you.",
        "system": "I can help with system operations. Some actions may require your approval.",
        "security": "I'll analyze that from a security perspective.",
    }
    
    state["specialist_response"] = responses.get(agent, "How can I help?")
    return state


# Build the graph structure (without LangGraph dependency for now)
# This will be compiled into a LangGraph StateGraph when the feature is enabled

AGENT_NODES = {
    "code": code_agent,
    "research": research_agent,
    "system": system_agent,
    "security": security_agent,
}


class SimpleOrchestrator:
    """
    Simple orchestrator that routes queries to specialist agents.
    
    This is a lightweight implementation that works without LangGraph.
    Can be upgraded to full LangGraph StateGraph for production.
    """
    
    def __init__(self):
        self.agents = AGENT_NODES
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query through the orchestrator.
        
        Returns:
            Dict with agent, requires_approval, pending_action, response
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
        specialist = route_to_specialist(state)
        
        # Run specialist agent
        agent_fn = self.agents.get(specialist, research_agent)
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

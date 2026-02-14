"""
ora.agents
==========

Agent system for OrA backend.

This package contains:
- BaseAgent: Abstract base class for all agents
- AgentFleet: Manages collection of agents with Byzantine consensus
- Specialized agents: Planner, Researcher, Builder, Tester, Integrator, Security, SelfDev
"""

from .base import BaseAgent
from .fleet import AgentFleet
from .planner import PlannerAgent
from .researcher import ResearcherAgent
from .builder import BuilderAgent
from .tester import TesterAgent
from .integrator import IntegratorAgent
from .security_agent import SecurityAgent
from .selfdev import SelfDevAgent

__all__ = [
    "BaseAgent",
    "AgentFleet",
    "PlannerAgent",
    "ResearcherAgent",
    "BuilderAgent",
    "TesterAgent",
    "IntegratorAgent",
    "SecurityAgent",
    "SelfDevAgent",
]
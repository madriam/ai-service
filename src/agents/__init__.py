# Agents module
from src.agents.registry import AgentRegistry, get_agent_registry
from src.agents.auto_parts import AutoPartsAgent
from src.agents.nurse import NurseAgent

__all__ = [
    "AgentRegistry",
    "get_agent_registry",
    "AutoPartsAgent",
    "NurseAgent",
]

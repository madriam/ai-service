"""
Agent Registry - Manages and routes to available agents.
"""
from typing import Optional
from functools import lru_cache
from src.agents.base import BaseAgent, AgentConfig, AgentResponse
from src.agents.auto_parts import AutoPartsAgent
from src.agents.nurse import NurseAgent
import structlog

logger = structlog.get_logger()


class AgentRegistry:
    """
    Registry for managing multiple AI agents.

    The registry can load agents from:
    1. Static configuration (predefined agents)
    2. Database (dynamic agents per organization)
    """

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._agent_types: dict[str, type[BaseAgent]] = {
            "auto_parts": AutoPartsAgent,
            "nurse": NurseAgent,
        }

    def register_agent(self, agent_id: str, agent: BaseAgent) -> None:
        """Register an agent instance."""
        self._agents[agent_id] = agent
        logger.info("Agent registered", agent_id=agent_id, agent_name=agent.name)

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def create_agent_from_config(self, config: AgentConfig) -> BaseAgent:
        """
        Create an agent from database configuration.

        This allows dynamic agent creation based on what's stored in
        the ai_agents table in conversation-service database.
        """
        # Check if there's a specific agent type for this config
        agent_type_name = config.settings.get("agent_type") if config.settings else None

        if agent_type_name and agent_type_name in self._agent_types:
            agent_class = self._agent_types[agent_type_name]
            return agent_class(config)

        # Default: Create a generic agent based on config
        return AutoPartsAgent(config)

    def load_static_agents(self) -> None:
        """Load predefined static agents for testing/demo."""
        # Auto Parts Agent
        auto_parts_config = AgentConfig(
            id="auto-parts",
            organization_id="123e4567-e89b-12d3-a456-426614174000",  # Test org
            name="Auto Pecas",
            system_prompt="",
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=1000,
            can_transfer=True,
            transfer_to=["human"],
            tools=[],
            settings={"agent_type": "auto_parts"},
        )
        self.register_agent(auto_parts_config.id, AutoPartsAgent(auto_parts_config))

        # Nurse Agent
        nurse_config = AgentConfig(
            id="nurse-virtual",
            organization_id="123e4567-e89b-12d3-a456-426614174001",  # Another org
            name="Enfermeira Virtual",
            system_prompt="",
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=1000,
            can_transfer=True,
            transfer_to=["human"],
            tools=[],
            settings={"agent_type": "nurse"},
        )
        self.register_agent(nurse_config.id, NurseAgent(nurse_config))

        logger.info("Static agents loaded", count=len(self._agents))

    async def process_message(
        self,
        agent_id: str,
        session_id: str,
        message: str,
    ) -> AgentResponse:
        """
        Process a message with the specified agent.

        Args:
            agent_id: The agent ID to use
            session_id: Session ID for conversation context
            message: User message

        Returns:
            AgentResponse with content and optional transfer info
        """
        agent = self.get_agent(agent_id)

        if not agent:
            logger.warning("Agent not found, using default", agent_id=agent_id)
            # Use first available agent as fallback
            if self._agents:
                agent = list(self._agents.values())[0]
            else:
                return AgentResponse(
                    content="Desculpe, nenhum agente disponivel no momento.",
                    transfer_to="human",
                    transfer_reason="no_agent_available",
                )

        return await agent.process_message(session_id, message)

    def list_agents(self) -> list[dict]:
        """List all registered agents."""
        return [
            {
                "id": agent_id,
                "name": agent.name,
                "description": agent.description,
            }
            for agent_id, agent in self._agents.items()
        ]


# Singleton registry
_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry instance."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
        _registry.load_static_agents()
    return _registry

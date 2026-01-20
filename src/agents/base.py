"""
Base agent class for all Agno agents.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass
from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.openai import OpenAIChat
from src.config import settings
import structlog

logger = structlog.get_logger()


@dataclass
class AgentResponse:
    """Response from an agent."""

    content: str
    transfer_to: Optional[str] = None  # agent_id, department_id, or "human"
    transfer_reason: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class AgentConfig:
    """Configuration for an agent loaded from database."""

    id: str
    organization_id: str
    name: str
    system_prompt: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 1000
    can_transfer: bool = True
    transfer_to: list[str] = None  # List of agent/department IDs
    tools: list[str] = None
    settings: dict = None


class BaseAgent(ABC):
    """Base class for all Agno agents."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self._agent: Optional[Agent] = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Agent description."""
        pass

    @abstractmethod
    def get_instructions(self) -> list[str]:
        """Get agent-specific instructions."""
        pass

    def get_tools(self) -> list:
        """Get agent tools. Override in subclass to add tools."""
        return []

    def _build_transfer_instructions(self) -> list[str]:
        """Build transfer instructions based on config."""
        if not self.config.can_transfer:
            return []

        instructions = [
            "",
            "=== TRANSFERENCIA DE CONVERSA ===",
            "",
            "Voce pode transferir a conversa quando necessario.",
            "Para transferir, inclua no final da sua resposta:",
            "[TRANSFER:tipo:id:motivo]",
            "",
            "Tipos de transferencia:",
            "- [TRANSFER:agent:ID_DO_AGENTE:motivo] - Transferir para outro agente AI",
            "- [TRANSFER:department:ID_DEPARTAMENTO:motivo] - Transferir para departamento",
            "- [TRANSFER:human:_:motivo] - Transferir para atendente humano",
            "",
            "Situacoes para transferir:",
            "- Cliente solicita explicitamente falar com humano/atendente",
            "- Problema fora do seu escopo de atuacao",
            "- Cliente demonstra frustracao ou insatisfacao",
            "- Assuntos sensiveis (financeiro, juridico, reclamacoes)",
            "- Voce nao consegue resolver o problema",
            "",
            "IMPORTANTE: Sempre responda normalmente e adicione a tag de transfer no final se necessario.",
        ]
        return instructions

    def create_agent(self, session_id: str) -> Agent:
        """Create an Agno agent instance for a session."""
        db = PostgresDb(db_url=settings.database_url)

        # Combine base instructions with agent-specific and transfer instructions
        all_instructions = self.get_instructions() + self._build_transfer_instructions()

        agent = Agent(
            model=OpenAIChat(
                id=self.config.model or settings.default_model,
                api_key=settings.openai_api_key,
            ),
            db=db,
            session_id=session_id,
            add_history_to_context=True,
            num_history_runs=10,
            instructions=all_instructions,
            tools=self.get_tools(),
        )

        return agent

    async def process_message(
        self,
        session_id: str,
        message: str,
    ) -> AgentResponse:
        """
        Process a message and return the response.

        Args:
            session_id: Unique session ID (user_id:conversation_id)
            message: User message

        Returns:
            AgentResponse with content and optional transfer info
        """
        agent = self.create_agent(session_id)

        logger.info(
            "Processing message",
            agent=self.name,
            session_id=session_id,
            message_preview=message[:50] if len(message) > 50 else message,
        )

        try:
            response = agent.run(message)
            content = response.content if response.content else ""

            # Parse transfer tag if present
            transfer_to = None
            transfer_reason = None

            if "[TRANSFER:" in content:
                # Extract transfer info: [TRANSFER:type:id:reason]
                import re

                match = re.search(r"\[TRANSFER:(\w+):([^:]+):([^\]]+)\]", content)
                if match:
                    transfer_type = match.group(1)
                    transfer_id = match.group(2)
                    transfer_reason = match.group(3)

                    if transfer_type == "human":
                        transfer_to = "human"
                    elif transfer_type == "agent":
                        transfer_to = f"agent:{transfer_id}"
                    elif transfer_type == "department":
                        transfer_to = f"department:{transfer_id}"

                    # Remove transfer tag from response
                    content = re.sub(r"\s*\[TRANSFER:[^\]]+\]", "", content).strip()

            logger.info(
                "Agent response generated",
                agent=self.name,
                session_id=session_id,
                has_transfer=transfer_to is not None,
            )

            return AgentResponse(
                content=content,
                transfer_to=transfer_to,
                transfer_reason=transfer_reason,
            )

        except Exception as e:
            logger.error("Agent error", agent=self.name, error=str(e))
            return AgentResponse(
                content="Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.",
                transfer_to="human",
                transfer_reason="error",
            )

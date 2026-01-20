# CLAUDE.md - AI Service

## Purpose

AI Agent service for the Madriam Platform. Processes AI requests via Kafka using Agno framework.

## Architecture

```
Kafka (ai.request) → AI Service → Agno Agent → Kafka (ai.response)
                         ↓
                  Agent Registry
                  ├── AutoPartsAgent
                  ├── NurseAgent
                  └── ... (more agents)
```

## Tech Stack

- **Language:** Python 3.11
- **AI Framework:** Agno
- **LLM:** OpenAI GPT-4o-mini (default)
- **Queue:** Kafka (Redpanda)
- **Database:** PostgreSQL (for Agno sessions)

## Quick Start

```bash
# Install dependencies
pip install uv
uv pip install --system -e .

# Set environment variables
export KAFKA_BROKERS=localhost:9092
export DATABASE_URL=postgresql://postgres:password@localhost:5432/ai_service
export OPENAI_API_KEY=sk-xxx

# Run
python -m src.main
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| KAFKA_BROKERS | Kafka broker addresses | localhost:9092 |
| KAFKA_CONSUMER_GROUP | Consumer group ID | ai-service |
| KAFKA_REQUEST_TOPIC | Topic for AI requests | ai.request |
| KAFKA_RESPONSE_TOPIC | Topic for AI responses | ai.response |
| DATABASE_URL | PostgreSQL for Agno sessions | - |
| OPENAI_API_KEY | OpenAI API key | - |
| LOG_LEVEL | Logging level | INFO |

## Kafka Message Formats

### ai.request (Input)
```json
{
  "conversation_id": "uuid",
  "organization_id": "uuid",
  "agent_id": "auto-parts",
  "message": "Preciso de pastilha de freio",
  "contact_id": "uuid",
  "metadata": {}
}
```

### ai.response (Output)
```json
{
  "conversation_id": "uuid",
  "organization_id": "uuid",
  "agent_id": "auto-parts",
  "content": "Olá! Para ajudá-lo com as pastilhas...",
  "transfer_to": null,
  "transfer_reason": null,
  "metadata": {}
}
```

## Adding New Agents

1. Create agent class in `src/agents/`:
```python
from src.agents.base import BaseAgent, AgentConfig

class MyNewAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "My Agent"

    @property
    def description(self) -> str:
        return "Description"

    def get_instructions(self) -> list[str]:
        return ["Instructions..."]
```

2. Register in `src/agents/registry.py`:
```python
self._agent_types["my_agent"] = MyNewAgent
```

## Transfer Feature

Agents can transfer conversations by including in their response:
```
[TRANSFER:type:id:reason]
```

Types:
- `[TRANSFER:human:_:cliente frustrado]` - Transfer to human
- `[TRANSFER:agent:nurse-virtual:assunto medico]` - Transfer to another agent
- `[TRANSFER:department:financeiro:cobranca]` - Transfer to department

## Project Structure

```
ai-service/
├── src/
│   ├── agents/
│   │   ├── base.py           # Base agent class
│   │   ├── auto_parts.py     # Auto parts agent
│   │   ├── nurse.py          # Nurse agent
│   │   └── registry.py       # Agent registry
│   ├── config.py             # Configuration
│   ├── kafka_service.py      # Kafka consumer/producer
│   └── main.py               # Entry point
├── k8s/base/                  # Kubernetes manifests
├── Dockerfile
└── pyproject.toml
```

## Deployment

Push to `main` triggers GitHub Actions:
1. Build and lint
2. Build Docker image
3. Push to ghcr.io/madriam/ai-service
4. ArgoCD syncs to Kubernetes

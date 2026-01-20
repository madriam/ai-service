# AI Service

AI Agent service for the Madriam Platform. Processes AI requests via Kafka using Agno framework.

## Agents

- **Auto Parts Agent** - Self-service for auto parts stores
- **Nurse Agent** - Healthcare guidance and appointment scheduling

## Quick Start

```bash
pip install uv
uv pip install --system -e .
python -m src.main
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| KAFKA_BROKERS | Kafka broker addresses |
| DATABASE_URL | PostgreSQL for Agno sessions |
| OPENAI_API_KEY | OpenAI API key |

See [CLAUDE.md](CLAUDE.md) for full documentation.

"""
Configuration for AI Service.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Kafka
    kafka_brokers: str = "localhost:9092"
    kafka_consumer_group: str = "ai-service"
    kafka_request_topic: str = "ai.request"
    kafka_response_topic: str = "ai.response"

    # Database (for Agno agent sessions)
    database_url: str = "postgresql://postgres:postgres@localhost:5432/ai_service"

    # OpenAI
    openai_api_key: str = ""

    # Anthropic (Claude)
    anthropic_api_key: str = ""

    # Default model settings
    default_model: str = "gpt-4o-mini"
    default_temperature: float = 0.7
    default_max_tokens: int = 1000

    # Service settings
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

"""
Kafka consumer and producer for AI Service.
"""
import asyncio
import json
from typing import Optional
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from src.config import settings
from src.agents.registry import get_agent_registry, AgentResponse
import structlog

logger = structlog.get_logger()


class KafkaService:
    """
    Kafka service for consuming AI requests and producing responses.
    """

    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.producer: Optional[AIOKafkaProducer] = None
        self._running = False

    async def start(self) -> None:
        """Start Kafka consumer and producer."""
        # Create consumer
        self.consumer = AIOKafkaConsumer(
            settings.kafka_request_topic,
            bootstrap_servers=settings.kafka_brokers,
            group_id=settings.kafka_consumer_group,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )

        # Create producer
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_brokers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        await self.consumer.start()
        await self.producer.start()

        logger.info(
            "Kafka service started",
            brokers=settings.kafka_brokers,
            consumer_topic=settings.kafka_request_topic,
            producer_topic=settings.kafka_response_topic,
        )

    async def stop(self) -> None:
        """Stop Kafka consumer and producer."""
        self._running = False

        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()

        logger.info("Kafka service stopped")

    async def process_messages(self) -> None:
        """
        Main loop to process incoming AI requests.

        Expected message format:
        {
            "conversation_id": "uuid",
            "organization_id": "uuid",
            "agent_id": "uuid or string",
            "message": "user message text",
            "contact_id": "uuid",
            "metadata": {}
        }
        """
        self._running = True
        registry = get_agent_registry()

        logger.info("Starting message processing loop")

        async for msg in self.consumer:
            if not self._running:
                break

            try:
                data = msg.value
                logger.info(
                    "Received AI request",
                    conversation_id=data.get("conversation_id"),
                    agent_id=data.get("agent_id"),
                )

                # Extract message data
                conversation_id = data.get("conversation_id")
                organization_id = data.get("organization_id")
                agent_id = data.get("agent_id")
                message = data.get("message", "")
                contact_id = data.get("contact_id")

                if not conversation_id or not message:
                    logger.warning("Invalid message: missing conversation_id or message")
                    continue

                # Create session ID for Agno (user:conversation format)
                session_id = f"{contact_id or 'unknown'}:{conversation_id}"

                # Process with agent
                response: AgentResponse = await registry.process_message(
                    agent_id=agent_id or "auto-parts",  # Default agent
                    session_id=session_id,
                    message=message,
                )

                # Build response message
                response_data = {
                    "conversation_id": conversation_id,
                    "organization_id": organization_id,
                    "agent_id": agent_id,
                    "content": response.content,
                    "transfer_to": response.transfer_to,
                    "transfer_reason": response.transfer_reason,
                    "metadata": response.metadata or {},
                }

                # Send response to Kafka
                await self.producer.send_and_wait(
                    settings.kafka_response_topic,
                    value=response_data,
                )

                logger.info(
                    "AI response sent",
                    conversation_id=conversation_id,
                    has_transfer=response.transfer_to is not None,
                )

            except Exception as e:
                logger.error(
                    "Error processing message",
                    error=str(e),
                    message=msg.value if msg else None,
                )

    async def send_response(
        self,
        conversation_id: str,
        organization_id: str,
        agent_id: str,
        content: str,
        transfer_to: Optional[str] = None,
        transfer_reason: Optional[str] = None,
    ) -> None:
        """
        Send an AI response to Kafka.
        """
        if not self.producer:
            raise RuntimeError("Kafka producer not started")

        response_data = {
            "conversation_id": conversation_id,
            "organization_id": organization_id,
            "agent_id": agent_id,
            "content": content,
            "transfer_to": transfer_to,
            "transfer_reason": transfer_reason,
        }

        await self.producer.send_and_wait(
            settings.kafka_response_topic,
            value=response_data,
        )


# Singleton service
_kafka_service: Optional[KafkaService] = None


def get_kafka_service() -> KafkaService:
    """Get the global Kafka service instance."""
    global _kafka_service
    if _kafka_service is None:
        _kafka_service = KafkaService()
    return _kafka_service

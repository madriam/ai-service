"""
AI Service - Main entry point.

A Kafka consumer service that processes AI requests using Agno agents.
"""
import asyncio
import logging
import signal
import sys
from src.config import settings
from src.kafka_service import get_kafka_service
from src.agents.registry import get_agent_registry
import structlog

# Configure standard logging first
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
print("AI Service module loaded", flush=True)


async def main() -> None:
    """Main entry point for the AI service."""
    logger.info(
        "Starting AI Service",
        kafka_brokers=settings.kafka_brokers,
        request_topic=settings.kafka_request_topic,
        response_topic=settings.kafka_response_topic,
    )

    # Initialize agent registry
    registry = get_agent_registry()
    logger.info("Agents loaded", agents=registry.list_agents())

    # Initialize Kafka service
    kafka_service = get_kafka_service()

    # Setup graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(sig: signal.Signals) -> None:
        logger.info("Received shutdown signal", signal=sig.name)
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    try:
        # Start Kafka service
        await kafka_service.start()

        # Process messages until shutdown
        process_task = asyncio.create_task(kafka_service.process_messages())

        # Wait for shutdown signal
        await shutdown_event.wait()

        # Cancel processing
        process_task.cancel()
        try:
            await process_task
        except asyncio.CancelledError:
            pass

    except Exception as e:
        logger.error("Error in main loop", error=str(e))
        raise

    finally:
        # Cleanup
        await kafka_service.stop()
        logger.info("AI Service stopped")


def run() -> None:
    """Run the service."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted")
        sys.exit(0)


if __name__ == "__main__":
    run()

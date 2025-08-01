import logging

logger = logging.getLogger(__name__)

def publish_message(queue_name: str, message: dict):
    """Publish message - RabbitMQ functionality removed"""
    logger.info(f"Message would be published to queue {queue_name}: {message}")
    return True

import json
import pika
from app.config import settings
from app.logger import logger
from typing import Any, Dict, Callable, Optional

# Initialize RabbitMQ connection
try:
    credentials = pika.PlainCredentials(
        settings.RABBITMQ_USER, 
        settings.RABBITMQ_PASSWORD
    )
    parameters = pika.ConnectionParameters(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
        virtual_host=settings.RABBITMQ_VHOST,
        credentials=credentials
    )
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    
    # Define exchanges
    channel.exchange_declare(
        exchange='chat_events',
        exchange_type='topic',
        durable=True
    )
    
    # Define queues
    channel.queue_declare(queue='chat.sessions', durable=True)
    channel.queue_declare(queue='chat.messages', durable=True)
    
    # Bind queues to exchanges
    channel.queue_bind(
        exchange='chat_events',
        queue='chat.sessions',
        routing_key='chat.session.*'
    )
    channel.queue_bind(
        exchange='chat_events',
        queue='chat.messages',
        routing_key='chat.message.*'
    )
    
    logger.info("RabbitMQ connection established")
except Exception as e:
    logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
    connection = None
    channel = None

def publish_message(routing_key: str, message: Dict[str, Any]) -> bool:
    """Publish a message to RabbitMQ"""
    if not channel:
        logger.warning("RabbitMQ channel not initialized")
        return False
    
    try:
        channel.basic_publish(
            exchange='chat_events',
            routing_key=routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
                content_type='application/json'
            )
        )
        return True
    except Exception as e:
        logger.error(f"Error publishing message: {str(e)}")
        return False

def publish_session_created(session_data: Dict[str, Any]) -> bool:
    """Publish session created event"""
    return publish_message('chat.session.created', session_data)

def publish_session_updated(session_data: Dict[str, Any]) -> bool:
    """Publish session updated event"""
    return publish_message('chat.session.updated', session_data)

def publish_message_created(message_data: Dict[str, Any]) -> bool:
    """Publish message created event"""
    return publish_message('chat.message.created', message_data)

def publish_analysis_linked(analysis_data: Dict[str, Any]) -> bool:
    """Publish analysis linked event"""
    return publish_message('chat.analysis.linked', analysis_data)

def setup_consumer(queue_name: str, callback: Callable) -> None:
    """Set up a consumer for a specific queue"""
    if not channel:
        logger.warning("RabbitMQ channel not initialized")
        return
    
    try:
        channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=False
        )
        logger.info(f"Consumer set up for queue {queue_name}")
    except Exception as e:
        logger.error(f"Error setting up consumer: {str(e)}")

def start_consuming() -> None:
    """Start consuming messages"""
    if not channel:
        logger.warning("RabbitMQ channel not initialized")
        return
    
    try:
        channel.start_consuming()
    except Exception as e:
        logger.error(f"Error consuming messages: {str(e)}")

def close_connection() -> None:
    """Close the RabbitMQ connection"""
    if connection:
        connection.close()
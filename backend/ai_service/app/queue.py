import json
import pika
from app.config import settings
from app.logger import logger
from typing import Dict, Any

def get_rabbitmq_connection():
    """Create and return a connection to RabbitMQ"""
    credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )
    return pika.BlockingConnection(parameters)

def publish_message(queue_name: str, message_data: Dict[str, Any]):
    """Publish a message to the specified queue"""
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Declare the queue (creates if doesn't exist)
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Convert message data to JSON string
        message_body = json.dumps(message_data)
        
        # Publish the message
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type='application/json'
            )
        )
        
        logger.info(f"Published message to queue '{queue_name}'")
        connection.close()
        
    except Exception as e:
        logger.error(f"Error publishing message to queue '{queue_name}': {str(e)}")
        # Don't re-raise the exception to prevent API failures due to queue issues

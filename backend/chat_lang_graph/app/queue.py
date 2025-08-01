import json
import pika
import time
import threading
from app.config import settings
from app.logger import logger
from typing import Any, Dict, Callable, Optional

# Global connection and channel variables
connection = None
channel = None

def establish_connection():
    """Establish a new connection to RabbitMQ with retry logic"""
    global connection, channel
    
    max_retries = 5
    retry_delay = 3  # seconds
    
    for attempt in range(max_retries):
        try:
            # Initialize RabbitMQ connection
            credentials = pika.PlainCredentials(
                username=getattr(settings, 'RABBITMQ_USER', 'guest'),
                password=getattr(settings, 'RABBITMQ_PASSWORD', 'guest')
            )
            
            connection_params = pika.ConnectionParameters(
                host=getattr(settings, 'RABBITMQ_HOST', 'localhost'),
                port=getattr(settings, 'RABBITMQ_PORT', 5672),
                credentials=credentials,
                heartbeat=60,
                blocked_connection_timeout=30,
                connection_attempts=3,
                retry_delay=1
            )
            
            connection = pika.BlockingConnection(connection_params)
            channel = connection.channel()
            
            # Define exchanges
            channel.exchange_declare(
                exchange='chat_langgraph_events',
                exchange_type='topic',
                durable=True
            )
            
            # Define queues
            channel.queue_declare(queue='chat_langgraph.sessions', durable=True)
            channel.queue_declare(queue='chat_langgraph.messages', durable=True)
            
            # Bind queues to exchanges
            channel.queue_bind(
                exchange='chat_langgraph_events',
                queue='chat_langgraph.sessions',
                routing_key='chat.session.*'
            )
            channel.queue_bind(
                exchange='chat_langgraph_events',
                queue='chat_langgraph.messages',
                routing_key='chat.message.*'
            )
            
            logger.info("RabbitMQ connection established for LangGraph service")
            return True
        except Exception as e:
            logger.warning(f"RabbitMQ connection attempt {attempt+1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    logger.error("Failed to establish RabbitMQ connection after multiple attempts")
    return False

def publish_message(routing_key: str, message: Dict[str, Any]) -> bool:
    """Publish a message to RabbitMQ"""
    global connection, channel
    
    # Check if connection is closed or doesn't exist
    if not connection or connection.is_closed:
        if not establish_connection():
            logger.error("Cannot publish message: Unable to establish RabbitMQ connection")
            return False
    
    try:
        # Publish message
        channel.basic_publish(
            exchange='chat_langgraph_events',
            routing_key=routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
                content_type='application/json'
            )
        )
        logger.debug(f"Published message to {routing_key}: {message}")
        return True
    except pika.exceptions.AMQPConnectionError:
        # Close and clear connection to force reconnect on next attempt
        try:
            if connection and not connection.is_closed:
                connection.close()
        except:
            pass
        connection = None
        channel = None
        return False
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

def close_connection() -> None:
    """Close the RabbitMQ connection"""
    global connection
    if connection and not connection.is_closed:
        try:
            connection.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {str(e)}")
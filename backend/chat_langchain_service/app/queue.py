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
                username=settings.RABBITMQ_USER,
                password=settings.RABBITMQ_PASSWORD
            )
            
            connection_params = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
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
            exchange='chat_events',
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

def publish_analysis_linked(analysis_data: Dict[str, Any]) -> bool:
    """Publish analysis linked event"""
    return publish_message('chat.analysis.linked', analysis_data)

def consume_message(queue_name: str):
    """Consume a message from a RabbitMQ queue (non-blocking)"""
    global connection, channel
    
    if not connection or connection.is_closed:
        if not establish_connection():
            return None
    
    try:
        # Ensure queue exists
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Get a message (non-blocking)
        method_frame, header_frame, body = channel.basic_get(queue=queue_name, auto_ack=True)
        
        if method_frame:
            message_str = body.decode('utf-8')
            message = json.loads(message_str)
            logger.debug(f"Message consumed from {queue_name}: {message}")
            return message
        return None
    except pika.exceptions.AMQPConnectionError:
        # Close and clear connection to force reconnect on next attempt
        try:
            if connection and not connection.is_closed:
                connection.close()
        except:
            pass
        connection = None
        channel = None
        return None
    except Exception as e:
        logger.error(f"Failed to consume message: {str(e)}")
        return None

def setup_consumer(queue_name: str, callback: Callable) -> None:
    """Set up a consumer for a specific queue"""
    global connection, channel
    
    if not connection or connection.is_closed:
        if not establish_connection():
            logger.error("Cannot set up consumer: Unable to establish RabbitMQ connection")
            return
    
    try:
        # Ensure queue exists
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Set up consumer
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
    global connection, channel
    
    if not connection or connection.is_closed:
        if not establish_connection():
            logger.error("Cannot start consuming: Unable to establish RabbitMQ connection")
            return
    
    try:
        channel.start_consuming()
    except Exception as e:
        logger.error(f"Error consuming messages: {str(e)}")

def start_consumers():
    """Start background consumers for different event queues"""
    # Set up consumers for different queues
    setup_consumer("chat.sessions", handle_session_event)
    setup_consumer("chat.messages", handle_message_event)
    
    # Start consuming in background thread
    consumer_thread = threading.Thread(target=start_consuming)
    consumer_thread.daemon = True
    consumer_thread.start()
    logger.info("Event consumers started in background")

def handle_session_event(ch, method, properties, body):
    """Handle session events"""
    try:
        message = json.loads(body)
        logger.debug(f"Received session event: {message}")
        # Process the session event
        # ...
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error handling session event: {str(e)}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def handle_message_event(ch, method, properties, body):
    """Handle message events"""
    try:
        message = json.loads(body)
        logger.debug(f"Received message event: {message}")
        # Process the message event
        # ...
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error handling message event: {str(e)}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def close_connection() -> None:
    """Close the RabbitMQ connection"""
    global connection
    if connection and not connection.is_closed:
        try:
            connection.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {str(e)}")

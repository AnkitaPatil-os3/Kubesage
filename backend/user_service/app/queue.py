import json
import pika
import time
from app.config import settings
from app.logger import logger

# RabbitMQ connection
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
                username=settings.RABBITMQ_USER if hasattr(settings, 'RABBITMQ_USER') else 'guest',
                password=settings.RABBITMQ_PASSWORD if hasattr(settings, 'RABBITMQ_PASSWORD') else 'guest'
            )
            
            connection_params = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST if hasattr(settings, 'RABBITMQ_HOST') else 'localhost',
                port=settings.RABBITMQ_PORT if hasattr(settings, 'RABBITMQ_PORT') else 5672,
                credentials=credentials,
                heartbeat=60,  # Reduced from 600
                blocked_connection_timeout=30,  # Reduced from 300
                connection_attempts=3,
                retry_delay=1
            )
            
            connection = pika.BlockingConnection(connection_params)
            channel = connection.channel()
            logger.info("RabbitMQ connection established")
            return True
        except Exception as e:
            logger.warning(f"RabbitMQ connection attempt {attempt+1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    logger.error("Failed to establish RabbitMQ connection after multiple attempts")
    return False

# Try to establish initial connection
try:
    establish_connection()
except Exception as e:
    logger.warning(f"Initial RabbitMQ connection failed: {str(e)}")

def publish_message(queue_name: str, message: dict):
    """Publish a message to a RabbitMQ queue with connection retry"""
    global connection, channel
    
    # Check if connection is closed or doesn't exist
    if not connection or connection.is_closed:
        if not establish_connection():
            logger.error("Cannot publish message: Unable to establish RabbitMQ connection")
            return False
    
    try:
        # Ensure queue exists
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Publish message
        message_str = json.dumps(message)
        channel.basic_publish(
            exchange='',  # Default exchange
            routing_key=queue_name,
            body=message_str,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type='application/json'
            )
        )
        logger.debug(f"Message published to {queue_name}: {message}")
        return True
    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"AMQP Connection error when publishing message: {str(e)}")
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
        logger.error(f"Failed to publish message: {str(e)}")
        return False

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

def setup_consumer(queue_name: str, callback):
    """Set up a consumer that will process messages as they arrive"""
    global connection, channel
    
    if not connection or connection.is_closed:
        if not establish_connection():
            logger.error(f"Failed to set up consumer for {queue_name}: Unable to establish connection")
            return False
    
    try:
        # Ensure queue exists
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Set up consumer
        def message_handler(ch, method, properties, body):
            try:
                message_str = body.decode('utf-8')
                message = json.loads(message_str)
                callback(message)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                # Still acknowledge to prevent message getting stuck
                ch.basic_ack(delivery_tag=method.delivery_tag)
        
        # Configure prefetch count to limit number of unacknowledged messages
        channel.basic_qos(prefetch_count=10)
        channel.basic_consume(queue=queue_name, on_message_callback=message_handler)
        logger.info(f"Consumer set up for queue {queue_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to set up consumer: {str(e)}")
        return False

def start_consuming():
    """Start consuming messages (this will block the thread)"""
    global channel
    if channel:
        try:
            channel.start_consuming()
        except Exception as e:
            logger.error(f"Error while consuming messages: {str(e)}")

def close_connection():
    """Close the RabbitMQ connection"""
    global connection
    if connection and not connection.is_closed:
        try:
            connection.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {str(e)}")
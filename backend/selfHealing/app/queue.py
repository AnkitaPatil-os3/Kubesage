import json
import pika
import uuid
import logging
import time
import threading
from typing import Dict, Any

logger = logging.getLogger(__name__)

class RabbitMQClient:
    def __init__(self, connection_params):
        self.connection_params = connection_params
        self.connection = None
        self.channel = None
        self.reconnect_delay = 5  # seconds
        self.is_consuming = False
        self._lock = threading.Lock()
        
    def connect(self):
        """Establish connection to RabbitMQ with retry logic"""
        if self.connection is not None and self.connection.is_open:
            return True
            
        try:
            logger.info("Connecting to RabbitMQ...")
            self.connection = pika.BlockingConnection(self.connection_params)
            self.channel = self.connection.channel()
            logger.info("Connected to RabbitMQ server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            return False
    
    def ensure_connection(self):
        """Ensure connection is established, reconnect if needed"""
        with self._lock:
            if self.connection is None or not self.connection.is_open:
                return self.connect()
            try:
                # Check connection by performing a harmless operation
                self.connection.process_data_events()
                return True
            except Exception as e:
                logger.warning(f"Connection check failed: {str(e)}, reconnecting...")
                try:
                    # Close the connection if it's still around
                    if self.connection:
                        self.connection.close()
                except Exception:
                    pass
                self.connection = None
                self.channel = None
                return self.connect()
    
    def publish_message(self, exchange, routing_key, message, properties=None):
        """Publish a message with connection retry"""
        max_retries = 3
        for attempt in range(max_retries):
            if not self.ensure_connection():
                logger.error("Failed to establish connection, cannot publish message")
                time.sleep(self.reconnect_delay)
                continue
                
            try:
                self.channel.basic_publish(
                    exchange=exchange,
                    routing_key=routing_key,
                    body=message,
                    properties=properties
                )
                logger.info(f"Published message with routing key {routing_key}")
                return True
            except Exception as e:
                logger.error(f"Error publishing message (attempt {attempt+1}/{max_retries}): {str(e)}")
                # Force reconnection on next attempt
                self.connection = None
                self.channel = None
                time.sleep(self.reconnect_delay)
        
        return False
    
    def start_consuming(self, queue_name, callback):
        """Start consuming messages with automatic reconnection"""
        self.is_consuming = True
        
        def consume_loop():
            while self.is_consuming:
                if not self.ensure_connection():
                    logger.error("Failed to establish connection, retrying...")
                    time.sleep(self.reconnect_delay)
                    continue
                
                try:
                    # Ensure queue exists
                    self.channel.queue_declare(queue=queue_name, durable=True)
                    
                    # Set up consumer
                    def message_handler(ch, method, properties, body):
                        try:
                            callback(ch, method, properties, body)
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                        except Exception as e:
                            logger.error(f"Error processing message: {str(e)}")
                            # Still acknowledge to prevent message getting stuck
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                    
                    # Configure prefetch count to limit number of unacknowledged messages
                    self.channel.basic_qos(prefetch_count=10)
                    self.channel.basic_consume(queue=queue_name, on_message_callback=message_handler)
                    logger.info(f"Starting to consume messages from {queue_name}")
                    
                    # Start consuming (this will block until connection is closed)
                    self.channel.start_consuming()
                except pika.exceptions.ConnectionClosedByBroker:
                    # Don't recover on channel errors
                    logger.warning("Connection closed by broker, reconnecting...")
                    time.sleep(self.reconnect_delay)
                except pika.exceptions.AMQPChannelError as e:
                    # Don't recover on channel errors
                    logger.error(f"AMQP Channel error: {e}, reconnecting...")
                    time.sleep(self.reconnect_delay)
                except pika.exceptions.AMQPConnectionError:
                    # Recover on connection errors
                    logger.warning("Connection was closed, reconnecting...")
                    time.sleep(self.reconnect_delay)
                except Exception as e:
                    logger.error(f"Error during message consumption: {str(e)}")
                    time.sleep(self.reconnect_delay)
        
        # Start consuming in a separate thread
        threading.Thread(target=consume_loop, daemon=True).start()
    
    def stop_consuming(self):
        """Stop consuming messages"""
        self.is_consuming = False
        if self.channel and self.channel.is_open:
            try:
                self.channel.stop_consuming()
            except Exception as e:
                logger.error(f"Error stopping consumer: {str(e)}")
    
    def close(self):
        """Close the connection"""
        if self.connection and self.connection.is_open:
            try:
                self.connection.close()
                logger.info("RabbitMQ connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")

# Initialize RabbitMQ client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create connection parameters
rabbitmq_params = pika.ConnectionParameters(
    host=os.getenv("RABBITMQ_HOST", "localhost"),
    port=int(os.getenv("RABBITMQ_PORT", "5672")),
    credentials=pika.PlainCredentials(
        username=os.getenv("RABBITMQ_USER", "guest"),
        password=os.getenv("RABBITMQ_PASSWORD", "guest")
    ),
    virtual_host=os.getenv("RABBITMQ_VHOST", "/"),
    heartbeat=60,
    blocked_connection_timeout=30
)

# Create RabbitMQ client instance
rabbitmq_client = RabbitMQClient(rabbitmq_params)

# Setup exchanges
def setup_exchanges():
    """Setup exchanges for self-healing events"""
    if rabbitmq_client.ensure_connection():
        try:
            # Declare exchanges
            rabbitmq_client.channel.exchange_declare(
                exchange='self_healing_events',
                exchange_type='topic',
                durable=True
            )
            logger.info("Exchanges setup complete")
        except Exception as e:
            logger.error(f"Error setting up exchanges: {str(e)}")

# Helper functions to publish events
def publish_event(routing_key: str, message: Dict[str, Any], correlation_id: str = None):
    """Generic function to publish an event"""
    if not rabbitmq_client.ensure_connection():
        logger.error(f"Failed to publish {routing_key} event: Connection not available")
        return False
    
    try:
        message_id = correlation_id or str(uuid.uuid4())
        properties = pika.BasicProperties(
            delivery_mode=2,  # make message persistent
            content_type='application/json',
            message_id=message_id,
            correlation_id=message_id,
            timestamp=int(time.time())
        )
        
        return rabbitmq_client.publish_message(
            exchange='self_healing_events',
            routing_key=routing_key,
            message=json.dumps(message),
            properties=properties
        )
    except Exception as e:
        logger.error(f"Error publishing {routing_key} event: {str(e)}")
        return False

# Specific event publishing functions
def publish_incident_created(incident_data: Dict[str, Any]):
    """Publish incident.created event"""
    return publish_event('incident.created', incident_data)

def publish_incident_updated(incident_data: Dict[str, Any]):
    """Publish incident.updated event"""
    return publish_event('incident.updated', incident_data)

def publish_plan_generated(plan_data: Dict[str, Any]):
    """Publish plan.generated event"""
    return publish_event('plan.generated', plan_data)

def publish_plan_executed(execution_data: Dict[str, Any]):
    """Publish plan.executed event"""
    return publish_event('plan.executed', execution_data)

def publish_remediation_failed(failure_data: Dict[str, Any]):
    """Publish remediation.failed event"""
    return publish_event('remediation.failed', failure_data)

def publish_remediation_succeeded(success_data: Dict[str, Any]):
    """Publish remediation.succeeded event"""
    return publish_event('remediation.succeeded', success_data)

# Event consumer setup
def setup_consumer(queue_name: str, callback):
    """Setup a consumer for a specific queue"""
    if rabbitmq_client.ensure_connection():
        try:
            # Declare queue
            rabbitmq_client.channel.queue_declare(queue=queue_name, durable=True)
            
            # Bind queue to exchange with appropriate routing key
            routing_key = queue_name.replace('_', '.')
            rabbitmq_client.channel.queue_bind(
                exchange='self_healing_events',
                queue=queue_name,
                routing_key=routing_key
            )
            
            # Start consuming
            rabbitmq_client.start_consuming(queue_name, callback)
            logger.info(f"Consumer setup complete for queue {queue_name}")
        except Exception as e:
            logger.error(f"Error setting up consumer for queue {queue_name}: {str(e)}")

# Call setup_exchanges on module import
setup_exchanges()

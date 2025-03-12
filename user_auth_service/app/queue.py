import json
import pika
import uuid
from typing import Dict, Any, Callable
from app.config import settings
from app.logger import logger

class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.event_handlers = {}
        self.connect()

    def connect(self):
        """Establish connection to RabbitMQ server"""
        try:
            parameters = pika.URLParameters(settings.RABBITMQ_URL)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            logger.info("Connected to RabbitMQ server")
            
            # Declare exchanges
            self.channel.exchange_declare(
                exchange='user_events',
                exchange_type='topic',
                durable=True
            )
            
            # Setup queues and bindings
            self.setup_queues()
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise

    def setup_queues(self):
        """Setup queues and bindings"""
        # User service queues
        self.channel.queue_declare(queue='user_created', durable=True)
        self.channel.queue_declare(queue='user_updated', durable=True)
        self.channel.queue_declare(queue='user_deleted', durable=True)
        
        # Bindings
        self.channel.queue_bind(
            exchange='user_events',
            queue='user_created',
            routing_key='user.created'
        )
        self.channel.queue_bind(
            exchange='user_events',
            queue='user_updated',
            routing_key='user.updated'
        )
        self.channel.queue_bind(
            exchange='user_events',
            queue='user_deleted',
            routing_key='user.deleted'
        )

    def publish_event(self, routing_key: str, message: Dict[str, Any], correlation_id: str = None):
        """Publish an event to RabbitMQ"""
        if not self.connection or self.connection.is_closed:
            self.connect()
            
        try:
            message_id = correlation_id or str(uuid.uuid4())
            self.channel.basic_publish(
                exchange='user_events',
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type='application/json',
                    message_id=message_id,
                    correlation_id=message_id
                )
            )
            logger.info(f"Published message with routing key {routing_key}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            raise
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register a handler for a specific event type"""
        self.event_handlers[event_type] = handler
    
    def start_consuming(self):
        """Start consuming messages from the queues"""
        if not self.connection or self.connection.is_closed:
            self.connect()
            
        for queue in ['user_created', 'user_updated', 'user_deleted']:
            self.channel.basic_consume(
                queue=queue,
                on_message_callback=self._process_message,
                auto_ack=False
            )
        
        logger.info("Starting to consume messages from RabbitMQ")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
        except Exception as e:
            logger.error(f"Error during message consumption: {str(e)}")
            self.channel.stop_consuming()
            
    def _process_message(self, ch, method, properties, body):
        """Process incoming messages"""
        try:
            event_type = method.routing_key
            message = json.loads(body)
            logger.info(f"Received message: {event_type} - {message}")
            
            if event_type in self.event_handlers:
                self.event_handlers[event_type](message)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                logger.warning(f"No handler for event type: {event_type}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def close(self):
        """Close the connection to RabbitMQ"""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("Closed connection to RabbitMQ")

# Create a singleton instance
rabbitmq_client = RabbitMQClient()

# Helper functions to publish common events
def publish_user_created(user_data: Dict[str, Any]):
    rabbitmq_client.publish_event('user.created', user_data)

def publish_user_updated(user_data: Dict[str, Any]):
    rabbitmq_client.publish_event('user.updated', user_data)

def publish_user_deleted(user_id: int):
    rabbitmq_client.publish_event('user.deleted', {'user_id': user_id})

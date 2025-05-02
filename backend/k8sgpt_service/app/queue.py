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
                exchange='k8sgpt_events',
                exchange_type='topic',
                durable=True
            )
            
            # Setup queues and bindings
            self.setup_queues()
            
            # Setup consumer for kubeconfig events
            self.setup_kubeconfig_events_consumer()
            
            # Setup consumer for user events
            self.setup_user_events_consumer()
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise

    def setup_queues(self):
        """Setup queues and bindings for K8sGPT events"""
        # K8sGPT service queues
        self.channel.queue_declare(queue='analysis_started', durable=True)
        self.channel.queue_declare(queue='analysis_completed', durable=True)
        self.channel.queue_declare(queue='analysis_failed', durable=True)
        self.channel.queue_declare(queue='backend_added', durable=True)
        self.channel.queue_declare(queue='backend_updated', durable=True)
        self.channel.queue_declare(queue='backend_deleted', durable=True)
        
        # Bindings
        event_types = [
            'analysis.started', 'analysis.completed', 'analysis.failed',
            'backend.added', 'backend.updated', 'backend.deleted'
        ]
        
        for event_type in event_types:
            queue_name = event_type.replace('.', '_')
            self.channel.queue_bind(
                exchange='k8sgpt_events',
                queue=queue_name,
                routing_key=event_type
            )

    def setup_kubeconfig_events_consumer(self):
        """Setup consumer for kubeconfig events"""
        # Declare kubeconfig events exchange
        self.channel.exchange_declare(
            exchange='kubeconfig_events',
            exchange_type='topic',
            durable=True
        )
        
        # Create queue for this service to consume kubeconfig events
        result = self.channel.queue_declare(
            queue='k8sgpt_service_kubeconfig_events',
            durable=True
        )
        queue_name = result.method.queue
        
        # Bind to kubeconfig events we're interested in
        self.channel.queue_bind(
            exchange='kubeconfig_events',
            queue=queue_name,
            routing_key='kubeconfig.activated'  # Listen for kubeconfig activation events
        )
        
        # Setup consumer
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=self._process_kubeconfig_event,
            auto_ack=False
        )

    def setup_user_events_consumer(self):
        """Setup consumer for user events"""
        # Declare user events exchange
        self.channel.exchange_declare(
            exchange='user_events',
            exchange_type='topic',
            durable=True
        )
        
        # Create queue for this service to consume user events
        result = self.channel.queue_declare(
            queue='k8sgpt_service_user_events',
            durable=True
        )
        queue_name = result.method.queue
        
        # Bind to user events we're interested in
        self.channel.queue_bind(
            exchange='user_events',
            queue=queue_name,
            routing_key='user.deleted'  # Listen for user deletion events
        )
        
        # Setup consumer
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=self._process_user_event,
            auto_ack=False
        )

    def publish_event(self, routing_key: str, message: Dict[str, Any], correlation_id: str = None):
        """Publish an event to RabbitMQ"""
        if not self.connection or self.connection.is_closed:
            self.connect()
            
        try:
            message_id = correlation_id or str(uuid.uuid4())
            self.channel.basic_publish(
                exchange='k8sgpt_events',
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
            
        logger.info("Starting to consume messages from RabbitMQ")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
        except Exception as e:
            logger.error(f"Error during message consumption: {str(e)}")
            self.channel.stop_consuming()
    
    def _process_kubeconfig_event(self, ch, method, properties, body):
        """Process kubeconfig events"""
        try:
            event_type = method.routing_key
            message = json.loads(body)
            logger.info(f"Received kubeconfig event: {event_type} - {message}")
            
            if event_type == 'kubeconfig.activated':
                # Handle kubeconfig activation event
                # This might trigger an automatic analysis or update cache
                logger.info(f"Kubeconfig activated: {message}")
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"Error processing kubeconfig event: {str(e)}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def _process_user_event(self, ch, method, properties, body):
        """Process user events"""
        try:
            event_type = method.routing_key
            message = json.loads(body)
            logger.info(f"Received user event: {event_type} - {message}")
            
            if event_type == 'user.deleted':
                # Handle user deletion event
                user_id = message.get('user_id')
                if user_id:
                    # Process user deletion (e.g., delete all user's analysis results)
                    from app.services import delete_user_data
                    delete_user_data(user_id)
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"Error processing user event: {str(e)}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def close(self):
        """Close the connection to RabbitMQ"""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("Closed connection to RabbitMQ")

# Create a singleton instance
rabbitmq_client = RabbitMQClient()

# Helper functions to publish common events
def publish_analysis_started(analysis_data: Dict[str, Any]):
    rabbitmq_client.publish_event('analysis.started', analysis_data)

def publish_analysis_completed(analysis_data: Dict[str, Any]):
    rabbitmq_client.publish_event('analysis.completed', analysis_data)

def publish_analysis_failed(analysis_data: Dict[str, Any]):
    rabbitmq_client.publish_event('analysis.failed', analysis_data)

def publish_backend_added(backend_data: Dict[str, Any]):
    rabbitmq_client.publish_event('backend.added', backend_data)

def publish_backend_updated(backend_data: Dict[str, Any]):
    rabbitmq_client.publish_event('backend.updated', backend_data)

def publish_backend_deleted(backend_data: Dict[str, Any]):
    rabbitmq_client.publish_event('backend.deleted', backend_data)

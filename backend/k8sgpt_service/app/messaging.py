import json
import pika
import logging
from typing import Callable, Dict, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class RabbitMQHandler:
    def __init__(self, host: str, port: int, user: str, password: str, vhost: str = '/'):
        self.credentials = pika.PlainCredentials(user, password)
        self.parameters = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=vhost,
            credentials=self.credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        self._connection = None
        self._channel = None

    @contextmanager
    def connection(self):
        """Context manager for RabbitMQ connection"""
        conn = self.connect()
        try:
            yield conn
        finally:
            self.close()

    def connect(self):
        """Establish connection to RabbitMQ"""
        if not self._connection or self._connection.is_closed:
            self._connection = pika.BlockingConnection(self.parameters)
            self._channel = self._connection.channel()
            logger.info("Connected to RabbitMQ")
        return self._connection

    def close(self):
        """Close the connection"""
        if self._connection and self._connection.is_open:
            self._connection.close()
            logger.info("Closed RabbitMQ connection")

    def declare_queue(self, queue_name: str, durable: bool = True):
        """Declare a queue"""
        self._channel.queue_declare(queue=queue_name, durable=durable)
        logger.info(f"Declared queue: {queue_name}")

    def publish_message(self, queue_name: str, message: Dict[str, Any]):
        """Publish a message to a queue"""
        self._channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
                content_type='application/json'
            )
        )
        logger.info(f"Published message to {queue_name}: {message}")

    def consume_messages(self, queue_name: str, callback: Callable[[Dict[str, Any]], None]):
        """Consume messages from a queue"""
        def _callback(ch, method, properties, body):
            try:
                message = json.loads(body)
                callback(message)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        self._channel.basic_qos(prefetch_count=1)
        self._channel.basic_consume(queue=queue_name, on_message_callback=_callback)
        logger.info(f"Started consuming from {queue_name}")
        self._channel.start_consuming()

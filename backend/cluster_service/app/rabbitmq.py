import json
import pika
import asyncio
from pika.adapters.asyncio_connection import AsyncioConnection
from app.config import settings
from app.logger import logger
from typing import Dict, Any
import uuid

# RabbitMQ connection variables
connection = None
channel = None

# Pending authentication requests: request_id -> asyncio.Future
pending_auth_requests = {}

def on_connection_open(connection):
    """Callback for when RabbitMQ connection is opened"""
    try:
        logger.info("RabbitMQ connection established")
        connection.channel(on_open_callback=on_channel_open)
    except Exception as e:
        logger.error(f"Error opening RabbitMQ channel: {str(e)}")
        if connection and not connection.is_closed:
            connection.close()

def on_channel_open(ch):
    """Callback for when RabbitMQ channel is opened"""
    global channel
    try:
        channel = ch
        logger.info("RabbitMQ channel opened")
        
        # Declare queues
        channel.queue_declare(queue='cluster_auth_requests', durable=True)
        channel.queue_declare(queue='cluster_auth_results', durable=True)
        channel.queue_declare(queue='cluster_namespace_requests', durable=True)
        channel.queue_declare(queue='cluster_namespace_results', durable=True)
        
        # Set up consumers
        channel.basic_consume(
            queue='cluster_auth_results', 
            on_message_callback=on_auth_result, 
            auto_ack=True
        )
        channel.basic_consume(
            queue='cluster_namespace_results', 
            on_message_callback=on_namespace_result, 
            auto_ack=True
        )
        
        logger.info("RabbitMQ consumers set up successfully")
        
    except Exception as e:
        logger.error(f"Error setting up RabbitMQ channel: {str(e)}")
        if channel and not channel.is_closed:
            channel.close()

def on_auth_result(ch, method, properties, body):
    """Handle authentication result from user service"""
    try:
        result = json.loads(body.decode('utf-8'))
        request_id = result.get('request_id')
        
        if request_id in pending_auth_requests:
            future = pending_auth_requests.pop(request_id)
            if not future.done():  # Check if future is still pending
                if result.get('error'):
                    future.set_exception(Exception(result['error']))
                else:
                    future.set_result(result)
        else:
            logger.warning(f"Received auth result for unknown request_id: {request_id}")
    except Exception as e:
        logger.error(f"Error processing auth result: {str(e)}")

def on_namespace_result(ch, method, properties, body):
    """Handle namespace result from agent via onboarding service"""
    try:
        result = json.loads(body.decode('utf-8'))
        request_id = result.get('request_id')
        
        if request_id in pending_auth_requests:  # Reusing the same dict for simplicity
            future = pending_auth_requests.pop(request_id)
            if not future.done():  # Check if future is still pending
                if result.get('error'):
                    future.set_exception(Exception(result['error']))
                else:
                    future.set_result(result)
        else:
            logger.warning(f"Received namespace result for unknown request_id: {request_id}")
    except Exception as e:
        logger.error(f"Error processing namespace result: {str(e)}")

def on_connection_closed(connection, reason):
    """Handle connection closure"""
    logger.warning(f"RabbitMQ connection closed: {reason}")
    # Implement reconnection logic if needed

def connect_to_rabbitmq():
    """Establish connection to RabbitMQ"""
    global connection
    try:
        logger.info("Initializing RabbitMQ connection...")
        credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=300,
            blocked_connection_timeout=30,
        )
        connection = AsyncioConnection(
            parameters=parameters,
            on_open_callback=on_connection_open,
            on_close_callback=on_connection_closed
        )
        logger.info("RabbitMQ connection request initiated...")
        return True
    except Exception as e:
        logger.error(f"Failed to initiate RabbitMQ connection: {str(e)}")
        return False

def is_rabbitmq_ready():
    """Check if RabbitMQ connection and channel are ready"""
    return (connection is not None and 
            not connection.is_closed and 
            channel is not None and 
            not channel.is_closed)

def publish_message(queue_name: str, message: dict):
    """Publish message to RabbitMQ queue"""
    if not is_rabbitmq_ready():
        logger.error("RabbitMQ connection/channel not ready")
        return False
    
    try:
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json'
            )
        )
        logger.info(f"Published message to {queue_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish message: {str(e)}")
        return False

async def authenticate_via_rabbitmq(api_key: str) -> Dict[str, Any]:
    """Authenticate API key via RabbitMQ to user service"""
    request_id = str(uuid.uuid4())
    
    # Create future for this request
    future = asyncio.Future()
    pending_auth_requests[request_id] = future
    
    # Publish authentication request
    auth_request = {
        "request_id": request_id,
        "api_key": api_key,
        "service": "cluster_service",
        "timestamp": asyncio.get_event_loop().time()
    }
    
    if not publish_message("cluster_auth_requests", auth_request):
        pending_auth_requests.pop(request_id, None)
        raise Exception("Failed to publish authentication request")
    
    try:
        # Wait for response with timeout
        result = await asyncio.wait_for(future, timeout=10.0)
        return result
    except asyncio.TimeoutError:
        pending_auth_requests.pop(request_id, None)
        raise Exception("Authentication timeout")

async def request_namespaces_via_websocket(agent_id: str, cluster_config: dict) -> Dict[str, Any]:
    """Request namespaces from agent via WebSocket through onboarding service"""
    request_id = str(uuid.uuid4())
    
    # Create future for this request
    future = asyncio.Future()
    pending_auth_requests[request_id] = future  # Reusing the same dict
    
    # Publish namespace request to onboarding service
    namespace_request = {
        "request_id": request_id,
        "agent_id": agent_id,
        "command": "get-namespaces",
        "cluster_config": cluster_config,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    if not publish_message("cluster_namespace_requests", namespace_request):
        pending_auth_requests.pop(request_id, None)
        raise Exception("Failed to publish namespace request")
    
    try:
        # Wait for response with timeout
        result = await asyncio.wait_for(future, timeout=30.0)
        return result
    except asyncio.TimeoutError:
        pending_auth_requests.pop(request_id, None)
        raise Exception("Namespace request timeout")

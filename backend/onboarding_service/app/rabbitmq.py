import json
import pika
import asyncio
from pika.adapters.asyncio_connection import AsyncioConnection
from threading import Thread
from app.config import settings
from app.logger import logger

# RabbitMQ connection variables
connection = None
channel = None

# Pending onboarding requests: request_id -> asyncio.Future
pending_requests = {}

# Pending API key validation requests: agent_id -> asyncio.Future
pending_api_key_validations = {}

# Pending namespace requests: request_id -> asyncio.Future
pending_namespace_requests = {}

def on_connection_open(connection):
    logger.info("RabbitMQ connection established")
    connection.channel(on_open_callback=on_channel_open)

def on_channel_open(ch):
    global channel
    channel = ch
    logger.info("RabbitMQ channel opened")
    # Declare the queues
    channel.queue_declare(queue='onboarding_requests', durable=True)
    channel.queue_declare(queue='onboarding_results', durable=True)
    channel.queue_declare(queue='api_key_validation_requests', durable=True)
    channel.queue_declare(queue='api_key_validation_results', durable=True)
    channel.queue_declare(queue='cluster_namespace_requests', durable=True)
    channel.queue_declare(queue='cluster_namespace_results', durable=True)
    channel.basic_consume(queue='onboarding_results', on_message_callback=on_onboarding_result, auto_ack=True)
    channel.basic_consume(queue='api_key_validation_results', on_message_callback=on_api_key_validation_result, auto_ack=True)
    channel.basic_consume(queue='cluster_namespace_requests', on_message_callback=on_namespace_request, auto_ack=True)

def on_onboarding_result(ch, method, properties, body):
    result = json.loads(body.decode('utf-8'))
    request_id = result.get('request_id')
    if request_id in pending_requests:
        future = pending_requests.pop(request_id)
        if result.get('error'):
            future.set_exception(Exception(result['error']))
        else:
            future.set_result(result)
    else:
        logger.warning(f"Received result for unknown request_id: {request_id}")

def on_api_key_validation_result(ch, method, properties, body):
    result = json.loads(body.decode('utf-8'))
    agent_id = result.get('agent_id')
    if agent_id in pending_api_key_validations:
        future = pending_api_key_validations.pop(agent_id)
        if result.get('error'):
            future.set_exception(Exception(result['error']))
        else:
            future.set_result(result)
    else:
        logger.warning(f"Received API key validation result for unknown agent_id: {agent_id}")

def on_namespace_request(ch, method, properties, body):
    """Handle namespace requests from cluster service"""
    try:
        import asyncio
        from app.websocket_client import send_message_to_agent
        
        request = json.loads(body.decode('utf-8'))
        request_id = request.get('request_id')
        agent_id = request.get('agent_id')
        cluster_config = request.get('cluster_config', {})
        
        logger.info(f"Received namespace request {request_id} for agent {agent_id}")
        
        # Create the message to send to the agent
        agent_message = {
            "request_id": request_id,
            "user": {"id": 1, "username": "system"},  # System request
            "request": {
                "message": "get-namespaces",
                **cluster_config
            }
        }
        
        # Send to agent via WebSocket (this will run in the event loop)
        async def send_to_agent():
            try:
                await send_message_to_agent(agent_id, agent_message)
                logger.info(f"Namespace request {request_id} sent to agent {agent_id}")
            except Exception as e:
                logger.error(f"Failed to send namespace request to agent {agent_id}: {str(e)}")
                # Send error result back to cluster service
                error_result = {
                    "request_id": request_id,
                    "error": f"Failed to communicate with agent: {str(e)}"
                }
                publish_message("cluster_namespace_results", error_result)
        
        # Schedule the async function
        loop = asyncio.get_event_loop()
        loop.create_task(send_to_agent())
        
    except Exception as e:
        logger.error(f"Error processing namespace request: {str(e)}")

def on_connection_closed(connection, reason):
    logger.warning(f"RabbitMQ connection closed: {reason}")
    # Try to reconnect after a delay
    import asyncio
    asyncio.get_event_loop().call_later(5, connect_to_rabbitmq)

def connect_to_rabbitmq():
    global connection
    credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=0,
        blocked_connection_timeout=30,
    )
    connection = AsyncioConnection(
        parameters=parameters,
        on_open_callback=on_connection_open,
        on_close_callback=on_connection_closed,
        custom_ioloop=asyncio.get_event_loop()
    )

def publish_message(queue_name: str, message: dict):
    if not channel or channel.is_closed:
        logger.error("RabbitMQ channel not available")
        return
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

def publish_api_key_validation_request(message: dict):
    """Publish API key validation request to user service"""
    if not channel or channel.is_closed:
        logger.error("RabbitMQ channel not available")
        return
    channel.basic_publish(
        exchange='',
        routing_key='api_key_validation_requests',
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type='application/json'
        )
    )
    logger.info(f"Published API key validation request for agent {message.get('agent_id')}")

import websockets
import json
import asyncio
from app.config import settings
from app.logger import logger
from typing import Dict, Any, Optional

# Connected agents: agent_id -> websocket connection
websocket_connections = {}

async def connect_to_agent(agent_id: str, agent_port: int = 9000) -> bool:
    """
    Establish WebSocket connection to a specific agent.
    
    Args:
        agent_id: The unique identifier of the agent
        agent_port: Port where agent WebSocket server is running
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        # For now, we assume agents are accessible via localhost
        # In production, this would be more sophisticated service discovery
        websocket_url = f"ws://localhost:{agent_port}/ws"
        
        logger.info(f"Attempting to connect to agent {agent_id} at {websocket_url}")
        
        websocket = await websockets.connect(
            websocket_url,
            timeout=settings.WEBSOCKET_TIMEOUT
        )
        
        # Store the connection
        websocket_connections[agent_id] = websocket
        
        logger.info(f"Successfully connected to agent {agent_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to connect to agent {agent_id}: {str(e)}")
        return False

async def send_request_to_agent(agent_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a request to an agent via WebSocket and wait for response.
    
    Args:
        agent_id: The unique identifier of the agent
        request: The request payload to send
    
    Returns:
        Dict containing the agent's response
    
    Raises:
        Exception: If agent is not connected or request fails
    """
    websocket = websocket_connections.get(agent_id)
    
    if not websocket:
        # Try to connect if not already connected
        if not await connect_to_agent(agent_id):
            raise Exception(f"Agent {agent_id} is not connected and connection failed")
        websocket = websocket_connections.get(agent_id)
    
    try:
        # Send request
        await websocket.send(json.dumps(request))
        logger.info(f"Sent request to agent {agent_id}: {request}")
        
        # Wait for response
        response = await asyncio.wait_for(
            websocket.recv(), 
            timeout=settings.WEBSOCKET_TIMEOUT
        )
        
        response_data = json.loads(response)
        logger.info(f"Received response from agent {agent_id}: {response_data}")
        
        return response_data
        
    except asyncio.TimeoutError:
        logger.error(f"Timeout waiting for response from agent {agent_id}")
        # Remove the connection as it might be stale
        websocket_connections.pop(agent_id, None)
        raise Exception(f"Timeout waiting for response from agent {agent_id}")
        
    except Exception as e:
        logger.error(f"Error communicating with agent {agent_id}: {str(e)}")
        # Remove the connection as it might be broken
        websocket_connections.pop(agent_id, None)
        raise Exception(f"Communication error with agent {agent_id}: {str(e)}")

async def disconnect_from_agent(agent_id: str):
    """
    Disconnect from a specific agent.
    
    Args:
        agent_id: The unique identifier of the agent
    """
    websocket = websocket_connections.pop(agent_id, None)
    if websocket:
        try:
            await websocket.close()
            logger.info(f"Disconnected from agent {agent_id}")
        except Exception as e:
            logger.error(f"Error disconnecting from agent {agent_id}: {str(e)}")

async def get_connected_agents() -> list:
    """
    Get list of currently connected agents.
    
    Returns:
        List of agent IDs that are currently connected
    """
    return list(websocket_connections.keys())

async def cleanup_connections():
    """
    Clean up all WebSocket connections.
    """
    for agent_id in list(websocket_connections.keys()):
        await disconnect_from_agent(agent_id)

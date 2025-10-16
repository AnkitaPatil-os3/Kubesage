from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
import json
import uuid
import asyncio
from typing import Optional
from app.config import settings
from app.logger import logger
from app.database import get_db
from app.models import ClusterConfig, Agent
from app.schemas import ClusterConfigRequest, ClusterConfigResponse, ClusterListResponse, GenerateAgentIdResponse
from app.auth import authenticate_request
from app.rabbitmq import publish_message, pending_requests, publish_api_key_validation_request
from app.rate_limiter import rate_limit
from app.websocket_client import send_message_to_agent
from sqlalchemy.orm import Session
import aiohttp

router = APIRouter()

@router.post("/onboard", response_model=ClusterConfigResponse, status_code=201)
async def onboard_cluster(
    cluster_data: ClusterConfigRequest,
    request: Request,
    session: Session = Depends(get_db),
    api_key: str = Depends(APIKeyHeader(name="X-API-Key")),
    agent_id: str = Depends(APIKeyHeader(name="agent_id", auto_error=True)),
    _: bool = Depends(rate_limit(max_requests=5, window_seconds=60)),  # Rate limit: 5 onboarding requests per minute
):
    """
    Agent sends this request with agent_id and api_key headers.
    """
    # Authenticate using API key
    user = await authenticate_request(api_key)
    current_user = user
    logger.info(f"Agent onboarding request received from agent {agent_id} for user {current_user['id']} with cluster {cluster_data.cluster_name}")

    try:
        # Validate agent_id belongs to the authenticated user
        agent = session.query(Agent).filter(
            Agent.agent_id == agent_id,
            Agent.user_id == current_user["id"]
        ).first()
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent with ID '{agent_id}' not found or does not belong to you")
        
        # Check if cluster already exists for this user
        existing_cluster = session.query(ClusterConfig).filter(
            ClusterConfig.cluster_name == cluster_data.cluster_name,
            ClusterConfig.user_id == current_user["id"]
        ).first()

        if existing_cluster:
            raise HTTPException(status_code=400, detail=f"Cluster '{cluster_data.cluster_name}' already exists for this user")

        # Create cluster in DB (no server_url or token needed for in-cluster agents)
        new_cluster = ClusterConfig(
            cluster_name=cluster_data.cluster_name,
            server_url="in-cluster",  # Placeholder for in-cluster config
            token="in-cluster-token",  # Placeholder for in-cluster token
            context_name=cluster_data.context_name,
            provider_name=cluster_data.provider_name,
            tags=json.dumps(cluster_data.tags) if cluster_data.tags else None,
            use_secure_tls=cluster_data.use_secure_tls,
            ca_data=None,  # Not needed for in-cluster
            tls_key=None,  # Not needed for in-cluster
            tls_cert=None,  # Not needed for in-cluster
            user_id=current_user["id"],
            cluster_metadata=json.dumps(cluster_data.metadata) if cluster_data.metadata else None
        )

        session.add(new_cluster)
        session.commit()
        session.refresh(new_cluster)

        # Update agent status and link to cluster
        agent.cluster_id = new_cluster.id
        agent.status = "connected"
        session.add(agent)
        session.commit()

        logger.info(f"Agent {agent_id} successfully onboarded cluster: {cluster_data.cluster_name}")

        # Create response
        response_data = ClusterConfigResponse(
            id=new_cluster.id,
            cluster_name=new_cluster.cluster_name,
            context_name=new_cluster.context_name,
            provider_name=new_cluster.provider_name,
            tags=json.loads(new_cluster.tags) if new_cluster.tags else None,
            use_secure_tls=new_cluster.use_secure_tls,
            user_id=new_cluster.user_id,
            is_operator_installed=new_cluster.is_operator_installed,
            created_at=new_cluster.created_at,
            updated_at=new_cluster.updated_at,
            message="Cluster onboarded successfully by agent",
            metadata=json.loads(new_cluster.cluster_metadata) if new_cluster.cluster_metadata else None
        )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error onboarding cluster: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/clusters", response_model=ClusterListResponse)
async def list_clusters(
    session: Session = Depends(get_db),
    api_key: str = Depends(APIKeyHeader(name="X-API-Key")),
):
    """
    Lists all onboarded clusters for the authenticated user.
    """
    # Authenticate
    user = await authenticate_request(api_key)

    current_user = user
    logger.info(f"Cluster list request received for user {current_user['id']}")

    try:
        # Query clusters for the user
        clusters = session.query(ClusterConfig).filter(
            ClusterConfig.user_id == current_user["id"]
        ).all()

        # Create response list
        cluster_responses = []
        for cluster in clusters:
            cluster_responses.append(ClusterConfigResponse(
                id=cluster.id,
                cluster_name=cluster.cluster_name,
                context_name=cluster.context_name,
                provider_name=cluster.provider_name,
                tags=json.loads(cluster.tags) if cluster.tags else None,
                use_secure_tls=cluster.use_secure_tls,
                user_id=cluster.user_id,
                is_operator_installed=cluster.is_operator_installed,
                created_at=cluster.created_at,
                updated_at=cluster.updated_at,
                message=None,
                metadata=json.loads(cluster.cluster_metadata) if cluster.cluster_metadata else None
            ))

        return ClusterListResponse(clusters=cluster_responses)

    except Exception as e:
        logger.error(f"Error listing clusters: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



@router.post("/generate-agent-id", response_model=GenerateAgentIdResponse)
async def generate_agent_id(
    request: Request,
    cluster_id: Optional[int] = None,
    session: Session = Depends(get_db),
    api_key: str = Depends(APIKeyHeader(name="X-API-Key")),
    _: bool = Depends(rate_limit(max_requests=10, window_seconds=60)),  # Rate limit: 10 agent ID generations per minute
):
    """
    Generate a unique agent ID for a cluster (optional) and validate API key.
    """
    # Authenticate
    user = await authenticate_request(api_key)
    current_user = user
    logger.info(f"Generate agent ID request for user {current_user['id']} cluster_id {cluster_id}")
    try:
        # Check if cluster exists and belongs to the user if cluster_id is provided
        if cluster_id is not None:
            cluster = session.query(ClusterConfig).filter(
                ClusterConfig.id == cluster_id,
                ClusterConfig.user_id == current_user["id"]
            ).first()
            if not cluster:
                raise HTTPException(status_code=404, detail=f"Cluster with ID '{cluster_id}' not found or does not belong to you")

        # Always generate agent_id as UUID, never use cluster_id
        agent_id = str(uuid.uuid4())
        new_agent = Agent(
            agent_id=agent_id,
            cluster_id=cluster_id,
            user_id=current_user["id"],
            status="pending"
        )
        session.add(new_agent)
        session.commit()
        session.refresh(new_agent)
        publish_api_key_validation_request({
            "agent_id": agent_id,
            "cluster_id": cluster_id,
            "user_id": current_user["id"],
            "api_key": api_key
        })
        cluster_name = cluster.cluster_name if cluster_id is not None and 'cluster' in locals() else "no cluster"
        logger.info(f"Generated agent ID {agent_id} for cluster {cluster_name}")
        return GenerateAgentIdResponse(
            agent_id=agent_id,
            cluster_id=cluster_id,
            status="pending",
            message="Agent ID generated successfully. API key validation in progress."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating agent ID: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


# Agent-based Kubernetes API endpoints
@router.get("/agent/{agent_id}/pods")
async def get_pods_via_agent(
    agent_id: str,
    namespace: str = "default",
    session: Session = Depends(get_db),
    api_key: str = Depends(APIKeyHeader(name="X-API-Key")),
):
    """Get pods from cluster via agent."""
    user = await authenticate_request(api_key)
    
    # Verify agent belongs to user
    agent = session.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.user_id == user["id"]
    ).first()
    
    if not agent or agent.status != "connected":
        raise HTTPException(status_code=404, detail="Agent not found or not connected")
    
    try:
        response = await send_message_to_agent(agent_id, {
            "action": "get-pods",
            "namespace": namespace
        })
        return response
    except Exception as e:
        logger.error(f"Error getting pods via agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent communication error: {str(e)}")


@router.get("/agent/{agent_id}/deployments")
async def get_deployments_via_agent(
    agent_id: str,
    namespace: str = "default",
    session: Session = Depends(get_db),
    api_key: str = Depends(APIKeyHeader(name="X-API-Key")),
):
    """Get deployments from cluster via agent."""
    user = await authenticate_request(api_key)
    
    agent = session.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.user_id == user["id"]
    ).first()
    
    if not agent or agent.status != "connected":
        raise HTTPException(status_code=404, detail="Agent not found or not connected")
    
    try:
        response = await send_message_to_agent(agent_id, {
            "action": "get-deployments",
            "namespace": namespace
        })
        return response
    except Exception as e:
        logger.error(f"Error getting deployments via agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent communication error: {str(e)}")


@router.get("/agent/{agent_id}/services")
async def get_services_via_agent(
    agent_id: str,
    namespace: str = "default",
    session: Session = Depends(get_db),
    api_key: str = Depends(APIKeyHeader(name="X-API-Key")),
):
    """Get services from cluster via agent."""
    user = await authenticate_request(api_key)
    
    agent = session.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.user_id == user["id"]
    ).first()
    
    if not agent or agent.status != "connected":
        raise HTTPException(status_code=404, detail="Agent not found or not connected")
    
    try:
        response = await send_message_to_agent(agent_id, {
            "action": "get-services",
            "namespace": namespace
        })
        return response
    except Exception as e:
        logger.error(f"Error getting services via agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent communication error: {str(e)}")


@router.get("/agent/{agent_id}/nodes")
async def get_nodes_via_agent(
    agent_id: str,
    session: Session = Depends(get_db),
    api_key: str = Depends(APIKeyHeader(name="X-API-Key")),
):
    """Get nodes from cluster via agent."""
    user = await authenticate_request(api_key)
    
    agent = session.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.user_id == user["id"]
    ).first()
    
    if not agent or agent.status != "connected":
        raise HTTPException(status_code=404, detail="Agent not found or not connected")
    
    try:
        response = await send_message_to_agent(agent_id, {
            "action": "get-nodes"
        })
        return response
    except Exception as e:
        logger.error(f"Error getting nodes via agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent communication error: {str(e)}")


@router.get("/agent/{agent_id}/cluster-resources")
async def get_cluster_resources_via_agent(
    agent_id: str,
    session: Session = Depends(get_db),
    api_key: str = Depends(APIKeyHeader(name="X-API-Key")),
):
    """Get cluster resources from cluster via agent."""
    user = await authenticate_request(api_key)
    
    agent = session.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.user_id == user["id"]
    ).first()
    
    if not agent or agent.status != "connected":
        raise HTTPException(status_code=404, detail="Agent not found or not connected")
    
    try:
        response = await send_message_to_agent(agent_id, {
            "action": "get-cluster-resources"
        })
        return response
    except Exception as e:
        logger.error(f"Error getting cluster resources via agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent communication error: {str(e)}")


@router.get("/agent/{agent_id}/pod-logs")
async def get_pod_logs_via_agent(
    agent_id: str,
    pod_name: str,
    namespace: str = "default",
    container: Optional[str] = None,
    lines: int = 100,
    session: Session = Depends(get_db),
    api_key: str = Depends(APIKeyHeader(name="X-API-Key")),
):
    """Get pod logs from cluster via agent."""
    user = await authenticate_request(api_key)
    
    agent = session.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.user_id == user["id"]
    ).first()
    
    if not agent or agent.status != "connected":
        raise HTTPException(status_code=404, detail="Agent not found or not connected")
    
    try:
        request_data = {
            "action": "get-pod-logs",
            "pod_name": pod_name,
            "namespace": namespace,
            "lines": lines
        }
        if container:
            request_data["container"] = container
            
        response = await send_message_to_agent(agent_id, request_data)
        return response
    except Exception as e:
        logger.error(f"Error getting pod logs via agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent communication error: {str(e)}")


@router.get("/agents")
async def list_agents(
    session: Session = Depends(get_db),
    api_key: str = Depends(APIKeyHeader(name="X-API-Key")),
):
    """List all agents for the authenticated user."""
    user = await authenticate_request(api_key)
    
    try:
        agents = session.query(Agent).filter(
            Agent.user_id == user["id"]
        ).all()
        
        agent_list = []
        for agent in agents:
            cluster_name = None
            if agent.cluster_id:
                cluster = session.query(ClusterConfig).filter(
                    ClusterConfig.id == agent.cluster_id
                ).first()
                if cluster:
                    cluster_name = cluster.cluster_name
            
            agent_list.append({
                "agent_id": agent.agent_id,
                "cluster_id": agent.cluster_id,
                "cluster_name": cluster_name,
                "status": agent.status,
                "created_at": agent.created_at,
                "updated_at": agent.updated_at
            })
        
        return {"agents": agent_list}
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


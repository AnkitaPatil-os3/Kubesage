from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session, select, update
from typing import List, Dict, Optional
import os, uuid, json, subprocess, shlex, datetime, tempfile, yaml, base64
from kubernetes import client, config
from kubernetes.client import Configuration, ApiClient
from app.database import get_session
from app.models import ClusterConfig
from app.schemas import (
    ClusterConfigRequest,
    ClusterConfigResponse,
    ClusterConfigList,
    MessageResponse
)
from app.auth import get_current_user
from app.config import settings
from app.logger import logger
from app.queue import publish_message
from app.llm_service import K8sLLMService
import httpx
import time
import requests
from collections import defaultdict



cluster_router = APIRouter()

#api 1 - onboard cluster       
@cluster_router.post("/onboard-cluster", response_model=ClusterConfigResponse, status_code=201,
                    summary="Onboard Cluster", 
                    description="Onboards a Kubernetes cluster using server URL, token, and optional TLS configuration")
async def onboard_cluster(
    cluster_data: ClusterConfigRequest,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Onboards a Kubernetes cluster using server URL, token, and optional TLS configuration.
    """
    logger.info(f"Cluster onboarding request received for user {current_user['id']} with cluster {cluster_data.cluster_name}")
    
    try:
        # Check if cluster already exists for this user
        existing_cluster = session.exec(
            select(ClusterConfig).where(
                ClusterConfig.cluster_name == cluster_data.cluster_name,
                ClusterConfig.user_id == current_user["id"]
            )
        ).first()
        
        if existing_cluster:
            raise HTTPException(status_code=400, detail=f"Cluster '{cluster_data.cluster_name}' already exists for this user")
        
        # REMOVED: Deactivate logic - no more active/inactive
        
        # Create new cluster record
        new_cluster = ClusterConfig(
            cluster_name=cluster_data.cluster_name,
            server_url=cluster_data.server_url,
            token=cluster_data.token,
            context_name=cluster_data.context_name,
            provider_name=cluster_data.provider_name,
            tags=cluster_data.tags,
            use_secure_tls=cluster_data.use_secure_tls,
            ca_data=cluster_data.ca_data if cluster_data.use_secure_tls else None,
            tls_key=cluster_data.tls_key if cluster_data.use_secure_tls else None,
            tls_cert=cluster_data.tls_cert if cluster_data.use_secure_tls else None,
            user_id=current_user["id"]
            # REMOVED: active=True
        )
        
        # Add to database
        session.add(new_cluster)
        session.commit()
        session.refresh(new_cluster)
        
        logger.info(f"User {current_user['id']} onboarded cluster: {cluster_data.cluster_name}")
        
        # Publish cluster onboarded event
        try:
            publish_message("cluster_events", {
                "event_type": "cluster_onboarded",
                "cluster_id": new_cluster.id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": cluster_data.cluster_name,
                "server_url": cluster_data.server_url,
                "provider_name": cluster_data.provider_name,
                "use_secure_tls": cluster_data.use_secure_tls,
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish message to queue: {str(queue_error)}")
        
        # Create response with success message
        response_data = ClusterConfigResponse(
            id=new_cluster.id,
            cluster_name=new_cluster.cluster_name,
            server_url=new_cluster.server_url,
            context_name=new_cluster.context_name,
            provider_name=new_cluster.provider_name,
            tags=new_cluster.tags,
            use_secure_tls=new_cluster.use_secure_tls,
            ca_data=new_cluster.ca_data,
            tls_key=new_cluster.tls_key,
            tls_cert=new_cluster.tls_cert,
            user_id=new_cluster.user_id,
            # REMOVED: active field
            is_operator_installed=new_cluster.is_operator_installed,
            created_at=new_cluster.created_at,
            updated_at=new_cluster.updated_at,
            message="Cluster onboarded successfully"
        )
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error onboarding cluster: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    """
    Onboards a Kubernetes cluster using server URL, token, and optional TLS configuration.
    
    - Accepts cluster configuration data
    - Creates a database record for the cluster
    - Publishes a cluster onboarding event to the message queue
    
    Parameters:
        cluster_data: The cluster configuration data
    
    Returns:
        ClusterConfigResponse: The created cluster record with success message
        
    Raises:
        HTTPException: 400 error if cluster already exists
        HTTPException: 500 error if onboarding fails
    """
    logger.info(f"Cluster onboarding request received for user {current_user['id']} with cluster {cluster_data.cluster_name}")
    
    try:
        # Check if cluster already exists for this user
        existing_cluster = session.exec(
            select(ClusterConfig).where(
                ClusterConfig.cluster_name == cluster_data.cluster_name,
                ClusterConfig.user_id == current_user["id"]
            )
        ).first()
        
        if existing_cluster:
            raise HTTPException(status_code=400, detail=f"Cluster '{cluster_data.cluster_name}' already exists for this user")
        
        # Deactivate all other clusters for this user
        session.exec(
            update(ClusterConfig)
            .where(ClusterConfig.user_id == current_user["id"])
            .values(active=False)
        )
        
        # Create new cluster record
        new_cluster = ClusterConfig(
            cluster_name=cluster_data.cluster_name,
            server_url=cluster_data.server_url,
            token=cluster_data.token,
            context_name=cluster_data.context_name,
            provider_name=cluster_data.provider_name,
            tags=cluster_data.tags,
            use_secure_tls=cluster_data.use_secure_tls,
            ca_data=cluster_data.ca_data if cluster_data.use_secure_tls else None,
            tls_key=cluster_data.tls_key if cluster_data.use_secure_tls else None,
            tls_cert=cluster_data.tls_cert if cluster_data.use_secure_tls else None,
            user_id=current_user["id"],
            active=True
        )
        
        # Add to database
        session.add(new_cluster)
        session.commit()
        session.refresh(new_cluster)
        
        logger.info(f"User {current_user['id']} onboarded cluster: {cluster_data.cluster_name}")
        
        # Publish cluster onboarded event
        try:
            publish_message("cluster_events", {
                "event_type": "cluster_onboarded",
                "cluster_id": new_cluster.id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": cluster_data.cluster_name,
                "server_url": cluster_data.server_url,
                "provider_name": cluster_data.provider_name,
                "use_secure_tls": cluster_data.use_secure_tls,
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish message to queue: {str(queue_error)}")
        
        # Create response with success message
        response_data = ClusterConfigResponse(
            id=new_cluster.id,
            cluster_name=new_cluster.cluster_name,
            server_url=new_cluster.server_url,
            context_name=new_cluster.context_name,
            provider_name=new_cluster.provider_name,
            tags=new_cluster.tags,
            use_secure_tls=new_cluster.use_secure_tls,
            ca_data=new_cluster.ca_data,
            tls_key=new_cluster.tls_key,
            tls_cert=new_cluster.tls_cert,
            user_id=new_cluster.user_id,
            active=new_cluster.active,
            is_operator_installed=new_cluster.is_operator_installed,
            created_at=new_cluster.created_at,
            updated_at=new_cluster.updated_at,
            message="Cluster onboarded successfully"
        )
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error onboarding cluster: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

#api 2 - list onboarded cluster        
@cluster_router.get("/clusters", response_model=ClusterConfigList,
                   summary="List Clusters", 
                   description="Returns a list of all onboarded clusters for the current user")
async def list_clusters(
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Lists all onboarded clusters for the current user.
    """
    try:
        clusters = session.exec(
            select(ClusterConfig)
            .where(ClusterConfig.user_id == current_user["id"])
            .order_by(ClusterConfig.created_at.desc())
        ).all()
        
        # Convert ClusterConfig models to ClusterConfigResponse models
        cluster_responses = []
        for cluster in clusters:
            cluster_response = ClusterConfigResponse(
                id=cluster.id,
                cluster_name=cluster.cluster_name,
                server_url=cluster.server_url,
                context_name=cluster.context_name,
                provider_name=cluster.provider_name,
                tags=cluster.tags,
                use_secure_tls=cluster.use_secure_tls,
                ca_data=cluster.ca_data,
                tls_key=cluster.tls_key,
                tls_cert=cluster.tls_cert,
                user_id=cluster.user_id,
                # REMOVED: active field
                is_operator_installed=cluster.is_operator_installed,
                created_at=cluster.created_at,
                updated_at=cluster.updated_at
            )
            cluster_responses.append(cluster_response)

        logger.info(f"Retrieved {len(cluster_responses)} clusters for user {current_user['id']}")
        return ClusterConfigList(clusters=cluster_responses)
        
    except Exception as e:
        logger.error(f"Error listing clusters for user {current_user['id']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving clusters: {str(e)}")


    """
    Sets a specific cluster as the active one for the user.
    
    Parameters:
        cluster_id: The ID of the cluster to activate
    
    Returns:
        JSONResponse: Success message
        
    Raises:
        HTTPException: 404 error if cluster not found
    """
    # Find the cluster to activate
    cluster_to_activate = session.exec(
        select(ClusterConfig).where(
            ClusterConfig.id == cluster_id,
            ClusterConfig.user_id == current_user["id"]
        )
    ).first()

    if not cluster_to_activate:
        raise HTTPException(status_code=404, detail=f"Cluster with ID '{cluster_id}' not found")
 
    # Deactivate all clusters for this user
    session.exec(
        update(ClusterConfig)
        .where(ClusterConfig.user_id == current_user["id"])
        .values(active=False)
    )
 
    # Activate the selected cluster
    cluster_to_activate.active = True
    session.add(cluster_to_activate)
    session.commit()

    logger.info(f"User {current_user['id']} activated cluster: {cluster_to_activate.cluster_name}")
    
    # Publish cluster activated event
    try:
        publish_message("cluster_events", {
            "event_type": "cluster_activated",
            "cluster_id": cluster_to_activate.id,
            "user_id": current_user["id"],
            "username": current_user.get("username", "unknown"),
            "cluster_name": cluster_to_activate.cluster_name,
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as queue_error:
        logger.warning(f"Failed to publish message to queue: {str(queue_error)}")
    
    return JSONResponse(content={"message": f"Cluster '{cluster_to_activate.cluster_name}' set as active"}, status_code=200)

#api 3 - remove cluster
@cluster_router.delete("/remove-cluster/{cluster_id}",
                      summary="Remove Cluster", 
                      description="Deletes a cluster configuration from the system")
async def remove_cluster(
    cluster_id: int,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Deletes a cluster configuration from the system.
    
    Parameters:
        cluster_id: The ID of the cluster to remove
    
    Returns:
        JSONResponse: Success message
        
    Raises:
        HTTPException: 404 error if cluster not found
    """
    # Check if the cluster exists and belongs to the current user
    cluster = session.exec(
        select(ClusterConfig).where(
            ClusterConfig.id == cluster_id,
            ClusterConfig.user_id == current_user["id"]
        )
    ).first()

    if not cluster:
        raise HTTPException(status_code=404, detail=f"Cluster with ID '{cluster_id}' not found or does not belong to you")
    
    cluster_name = cluster.cluster_name
    
    try:
        # Remove the entry from the database
        session.delete(cluster)
        session.commit()
        
        # Publish cluster deleted event
        try:
            publish_message("cluster_events", {
                "event_type": "cluster_deleted",
                "cluster_id": cluster_id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": cluster_name,
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish message to queue: {str(queue_error)}")
    
        logger.info(f"User {current_user['id']} removed cluster {cluster_name}")
        return JSONResponse(content={
            "message": f"Cluster '{cluster_name}' successfully removed"
        }, status_code=200)
    except Exception as e:
        # If an error occurs, rollback the database transaction
        session.rollback()
        logger.error(f"Error removing cluster: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error removing cluster: {str(e)}")

#api 4 - select-cluster-and-get-namespaces     

@cluster_router.post("/select-cluster-and-get-namespaces/{cluster_id}",
                    summary="Select Cluster and Get Namespaces", 
                    description="Gets namespaces from a specific cluster using server URL and token")
async def select_cluster_and_get_namespaces(
    cluster_id: int,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Gets namespaces from a specific cluster using server URL and token dynamically.
    
    This endpoint:
    1. Validates that the cluster exists and belongs to the user
    2. Uses the cluster's server URL and token to connect
    3. Retrieves and returns the namespace list from the cluster
    
    Parameters:
        cluster_id: The ID of the cluster to get namespaces from
    
    Returns:
        JSONResponse: Contains cluster info and namespace list
        
    Raises:
        HTTPException: 404 error if cluster not found
        HTTPException: 500 error if namespace retrieval fails
    """
    logger.info(f"Select cluster and get namespaces request for user {current_user['id']} with cluster ID {cluster_id}")
    
    try:
        # Step 1: Find the cluster
        cluster = session.exec(
            select(ClusterConfig).where(
                ClusterConfig.id == cluster_id,
                ClusterConfig.user_id == current_user["id"]
            )
        ).first()

        if not cluster:
            raise HTTPException(
                status_code=404, 
                detail=f"Cluster with ID '{cluster_id}' not found or does not belong to you"
            )

        logger.info(f"User {current_user['id']} accessing cluster: {cluster.cluster_name}")

        # Step 2: Get namespaces using server URL and token dynamically
        try:
            # Create Kubernetes configuration using the cluster's data
            from kubernetes.client import Configuration, ApiClient
            
            configuration = Configuration()
            configuration.host = cluster.server_url
            configuration.api_key = {"authorization": f"Bearer {cluster.token}"}
            configuration.api_key_prefix = {"authorization": ""}
            
            # Configure TLS based on cluster settings
            if cluster.use_secure_tls:
                configuration.verify_ssl = True
                
                # Handle CA certificate if provided
                if cluster.ca_data:
                    import tempfile
                    import base64
                    
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.crt') as ca_file:
                        try:
                            ca_content = base64.b64decode(cluster.ca_data).decode('utf-8')
                        except:
                            ca_content = cluster.ca_data
                        ca_file.write(ca_content)
                        configuration.ssl_ca_cert = ca_file.name
                
                # Handle client certificates if provided
                if cluster.tls_cert and cluster.tls_key:
                    import tempfile
                    import base64
                    
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.crt') as cert_file:
                        try:
                            cert_content = base64.b64decode(cluster.tls_cert).decode('utf-8')
                        except:
                            cert_content = cluster.tls_cert
                        cert_file.write(cert_content)
                        configuration.cert_file = cert_file.name
                    
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.key') as key_file:
                        try:
                            key_content = base64.b64decode(cluster.tls_key).decode('utf-8')
                        except:
                            key_content = cluster.tls_key
                        key_file.write(key_content)
                        configuration.key_file = key_file.name
            else:
                configuration.verify_ssl = False

            # Create API client and get namespaces
            api_client = ApiClient(configuration)
            v1 = client.CoreV1Api(api_client)
            
            logger.info(f"Retrieving namespaces from cluster: {cluster.cluster_name}")
            namespace_list = v1.list_namespace()
            namespaces = [ns.metadata.name for ns in namespace_list.items]
            
            logger.info(f"Successfully retrieved {len(namespaces)} namespaces from cluster {cluster.cluster_name}")

        except client.rest.ApiException as e:
            logger.error(f"Kubernetes API error while getting namespaces: Status={e.status}, Reason={e.reason}")
            return JSONResponse(content={
                "success": False,
                "cluster_info": {
                    "id": cluster.id,
                    "cluster_name": cluster.cluster_name,
                    "server_url": cluster.server_url,
                    "provider_name": cluster.provider_name
                },
                "namespaces_retrieved": False,
                "namespaces": [],
                "error": f"Failed to retrieve namespaces: {e.reason}",
                "message": f"Cluster '{cluster.cluster_name}' accessible, but namespace retrieval failed"
            }, status_code=200)

        except Exception as e:
            logger.error(f"Error retrieving namespaces: {str(e)}")
            return JSONResponse(content={
                "success": False,
                "cluster_info": {
                    "id": cluster.id,
                    "cluster_name": cluster.cluster_name,
                    "server_url": cluster.server_url,
                    "provider_name": cluster.provider_name
                },
                "namespaces_retrieved": False,
                "namespaces": [],
                "error": f"Failed to retrieve namespaces: {str(e)}",
                "message": f"Cluster '{cluster.cluster_name}' accessible, but namespace retrieval failed"
            }, status_code=200)

        # Step 3: Publish events
        try:
            publish_message("cluster_events", {
                "event_type": "cluster_selected_and_namespaces_retrieved",
                "cluster_id": cluster.id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": cluster.cluster_name,
                "namespace_count": len(namespaces),
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish message to queue: {str(queue_error)}")

        # Step 4: Return success response with cluster info and namespaces
        return JSONResponse(content={
            "success": True,
            "namespaces_retrieved": True,
            "cluster_info": {
                "id": cluster.id,
                "cluster_name": cluster.cluster_name,
                "server_url": cluster.server_url,
                "context_name": cluster.context_name,
                "provider_name": cluster.provider_name,
                "tags": cluster.tags,
                "use_secure_tls": cluster.use_secure_tls,
                "is_operator_installed": cluster.is_operator_installed,
                "created_at": cluster.created_at.isoformat() if cluster.created_at else None,
                "updated_at": cluster.updated_at.isoformat() if cluster.updated_at else None
            },
            "namespaces": namespaces,
            "namespace_count": len(namespaces),
            "message": f"Successfully retrieved {len(namespaces)} namespaces from cluster '{cluster.cluster_name}'"
        }, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in select cluster and get namespaces: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    """
    Selects a specific cluster, activates it, and returns its namespace list.
    
    This endpoint combines cluster activation and namespace retrieval in a single operation:
    1. Validates that the cluster exists and belongs to the user
    2. Deactivates all other clusters for the user
    3. Activates the selected cluster
    4. Retrieves and returns the namespace list from the newly active cluster
    
    Parameters:
        cluster_id: The ID of the cluster to select and activate
    
    Returns:
        JSONResponse: Contains cluster info, activation status, and namespace list
        
    Raises:
        HTTPException: 404 error if cluster not found
        HTTPException: 500 error if cluster activation or namespace retrieval fails
    """
    logger.info(f"Cluster selection and namespace retrieval request for user {current_user['id']} with cluster ID {cluster_id}")
    
    try:
        # Step 1: Find the cluster to activate
        cluster_to_activate = session.exec(
            select(ClusterConfig).where(
                ClusterConfig.id == cluster_id,
                ClusterConfig.user_id == current_user["id"]
            )
        ).first()

        if not cluster_to_activate:
            raise HTTPException(
                status_code=404, 
                detail=f"Cluster with ID '{cluster_id}' not found or does not belong to you"
            )

        # Step 2: Deactivate all clusters for this user
        session.exec(
            update(ClusterConfig)
            .where(ClusterConfig.user_id == current_user["id"])
            .values(active=False)
        )

        # Step 3: Activate the selected cluster
        cluster_to_activate.active = True
        session.add(cluster_to_activate)
        session.commit()

        logger.info(f"User {current_user['id']} activated cluster: {cluster_to_activate.cluster_name}")

        # Step 4: Get namespaces from the newly active cluster
        try:
            # Create Kubernetes configuration using the selected cluster's data
            from kubernetes.client import Configuration, ApiClient
            
            configuration = Configuration()
            configuration.host = cluster_to_activate.server_url
            configuration.api_key = {"authorization": f"Bearer {cluster_to_activate.token}"}
            configuration.api_key_prefix = {"authorization": ""}
            
            # Configure TLS based on cluster settings
            if cluster_to_activate.use_secure_tls:
                configuration.verify_ssl = True
                
                # Handle CA certificate if provided
                if cluster_to_activate.ca_data:
                    import tempfile
                    import base64
                    
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.crt') as ca_file:
                        try:
                            ca_content = base64.b64decode(cluster_to_activate.ca_data).decode('utf-8')
                        except:
                            ca_content = cluster_to_activate.ca_data
                        ca_file.write(ca_content)
                        configuration.ssl_ca_cert = ca_file.name
                
                # Handle client certificates if provided
                if cluster_to_activate.tls_cert and cluster_to_activate.tls_key:
                    import tempfile
                    import base64
                    
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.crt') as cert_file:
                        try:
                            cert_content = base64.b64decode(cluster_to_activate.tls_cert).decode('utf-8')
                        except:
                            cert_content = cluster_to_activate.tls_cert
                        cert_file.write(cert_content)
                        configuration.cert_file = cert_file.name
                    
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.key') as key_file:
                        try:
                            key_content = base64.b64decode(cluster_to_activate.tls_key).decode('utf-8')
                        except:
                            key_content = cluster_to_activate.tls_key
                        key_file.write(key_content)
                        configuration.key_file = key_file.name
            else:
                configuration.verify_ssl = False

            # Create API client and get namespaces
            api_client = ApiClient(configuration)
            v1 = client.CoreV1Api(api_client)
            
            logger.info(f"Retrieving namespaces from cluster: {cluster_to_activate.cluster_name}")
            namespace_list = v1.list_namespace()
            namespaces = [ns.metadata.name for ns in namespace_list.items]
            
            logger.info(f"Successfully retrieved {len(namespaces)} namespaces from cluster {cluster_to_activate.cluster_name}")

        except client.rest.ApiException as e:
            logger.error(f"Kubernetes API error while getting namespaces: Status={e.status}, Reason={e.reason}")
            # Cluster was activated successfully, but namespace retrieval failed
            return JSONResponse(content={
                "success": True,
                "cluster_activated": True,
                "cluster_info": {
                    "id": cluster_to_activate.id,
                    "cluster_name": cluster_to_activate.cluster_name,
                    "server_url": cluster_to_activate.server_url,
                    "provider_name": cluster_to_activate.provider_name,
                    "active": True
                },
                "namespaces_retrieved": False,
                "namespaces": [],
                "error": f"Cluster activated successfully, but failed to retrieve namespaces: {e.reason}",
                "message": f"Cluster '{cluster_to_activate.cluster_name}' activated, but namespace retrieval failed"
            }, status_code=200)

        except Exception as e:
            logger.error(f"Error retrieving namespaces: {str(e)}")
            # Cluster was activated successfully, but namespace retrieval failed
            return JSONResponse(content={
                "success": True,
                "cluster_activated": True,
                "cluster_info": {
                    "id": cluster_to_activate.id,
                    "cluster_name": cluster_to_activate.cluster_name,
                    "server_url": cluster_to_activate.server_url,
                    "provider_name": cluster_to_activate.provider_name,
                    "active": True
                },
                "namespaces_retrieved": False,
                "namespaces": [],
                "error": f"Cluster activated successfully, but failed to retrieve namespaces: {str(e)}",
                "message": f"Cluster '{cluster_to_activate.cluster_name}' activated, but namespace retrieval failed"
            }, status_code=200)

        # Step 5: Publish events
        try:
            # Publish cluster activated event
            publish_message("cluster_events", {
                "event_type": "cluster_selected_and_activated",
                "cluster_id": cluster_to_activate.id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": cluster_to_activate.cluster_name,
                "namespace_count": len(namespaces),
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish message to queue: {str(queue_error)}")

        # Step 6: Return success response with cluster info and namespaces
        return JSONResponse(content={
            "success": True,
            "cluster_activated": True,
            "namespaces_retrieved": True,
            "cluster_info": {
                "id": cluster_to_activate.id,
                "cluster_name": cluster_to_activate.cluster_name,
                "server_url": cluster_to_activate.server_url,
                "context_name": cluster_to_activate.context_name,
                "provider_name": cluster_to_activate.provider_name,
                "tags": cluster_to_activate.tags,
                "use_secure_tls": cluster_to_activate.use_secure_tls,
                "is_operator_installed": cluster_to_activate.is_operator_installed,
                "active": True,
                "created_at": cluster_to_activate.created_at.isoformat() if cluster_to_activate.created_at else None,
                "updated_at": cluster_to_activate.updated_at.isoformat() if cluster_to_activate.updated_at else None
            },
            "namespaces": namespaces,
            "namespace_count": len(namespaces),
            "message": f"Cluster '{cluster_to_activate.cluster_name}' activated successfully and {len(namespaces)} namespaces retrieved"
        }, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in select cluster and get namespaces: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@cluster_router.get("/get-namespaces/{cluster_id}",
                   summary="Get Namespaces from Specific Cluster", 
                   description="Retrieves namespaces from the specified cluster using GET method")
async def get_namespaces_from_cluster(
    cluster_id: int,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Retrieves namespaces from the specified cluster using GET method.
    
    Parameters:
        cluster_id: The ID of the cluster to get namespaces from
    
    Returns:
        JSONResponse: Cluster details and list of namespaces
        
    Raises:
        HTTPException: 404 error if cluster not found
        HTTPException: 500 error if namespace retrieval fails
    """
    logger.info(f"GET namespaces request for cluster ID {cluster_id} by user {current_user['id']}")
    
    # Get the specified cluster
    cluster = session.exec(
        select(ClusterConfig).where(
            ClusterConfig.id == cluster_id,
            ClusterConfig.user_id == current_user["id"]
        )
    ).first()
    
    if not cluster:
        logger.warning(f"Cluster with ID {cluster_id} not found for user {current_user['id']}")
        raise HTTPException(
            status_code=404, 
            detail=f"Cluster with ID '{cluster_id}' not found or you don't have access to it"
        )

    try:
        # Create Kubernetes configuration using cluster data
        from kubernetes.client import Configuration, ApiClient
        
        configuration = Configuration()
        configuration.host = cluster.server_url
        configuration.api_key = {"authorization": f"Bearer {cluster.token}"}
        configuration.api_key_prefix = {"authorization": ""}
        configuration.verify_ssl = cluster.use_secure_tls
        
        logger.info(f"Connecting to cluster '{cluster.cluster_name}' at {cluster.server_url}")
        
        # Configure TLS if needed
        if cluster.use_secure_tls and cluster.ca_data:
            import tempfile
            import base64
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.crt') as ca_file:
                try:
                    ca_content = base64.b64decode(cluster.ca_data).decode('utf-8')
                except:
                    ca_content = cluster.ca_data
                ca_file.write(ca_content)
                configuration.ssl_ca_cert = ca_file.name
        
        # Create API client and get namespaces
        api_client = ApiClient(configuration)
        v1 = client.CoreV1Api(api_client)
        
        # List all namespaces
        namespace_list = v1.list_namespace()
        namespaces = [ns.metadata.name for ns in namespace_list.items]
        
        logger.info(f"Successfully retrieved {len(namespaces)} namespaces from cluster '{cluster.cluster_name}'")
        
        # Publish namespace retrieval event
        try:
            publish_message("cluster_events", {
                "event_type": "namespaces_retrieved_by_cluster_id",
                "cluster_id": cluster_id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": cluster.cluster_name,
                "namespace_count": len(namespaces),
                "method": "GET",
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish namespace retrieval event: {str(queue_error)}")
        
        return JSONResponse(content={
            "success": True,
            "cluster_id": cluster_id,
            "cluster_name": cluster.cluster_name,
            "server_url": cluster.server_url,
            "provider_name": cluster.provider_name,
            "context_name": cluster.context_name,
            "use_secure_tls": cluster.use_secure_tls,
            "namespace_count": len(namespaces),
            "namespaces": namespaces,
            "retrieved_at": datetime.datetime.now().isoformat()
        }, status_code=200)
    
    except client.rest.ApiException as e:
        logger.error(f"Kubernetes API error for cluster ID {cluster_id}: Status={e.status}, Reason={e.reason}")
        
        # Publish failure event
        try:
            publish_message("cluster_events", {
                "event_type": "namespaces_retrieval_failed_by_cluster_id",
                "cluster_id": cluster_id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": cluster.cluster_name,
                "error": f"API Error: {e.status} - {e.reason}",
                "method": "GET",
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish error event: {str(queue_error)}")
        
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching namespaces from cluster '{cluster.cluster_name}': {e.reason}"
        )
    
    except Exception as e:
        logger.error(f"Error fetching namespaces from cluster ID {cluster_id}: {str(e)}")
        
        # Publish failure event
        try:
            publish_message("cluster_events", {
                "event_type": "namespaces_retrieval_failed_by_cluster_id",
                "cluster_id": cluster_id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": cluster.cluster_name,
                "error": str(e),
                "method": "GET",
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish error event: {str(queue_error)}")
        
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching namespaces from cluster '{cluster.cluster_name}': {str(e)}"
        )
    """
    Retrieves namespaces from the specified cluster.
    """
    # Get the specified cluster
    cluster = session.exec(
        select(ClusterConfig).where(
            ClusterConfig.id == cluster_id,
            ClusterConfig.user_id == current_user["id"]
        )
    ).first()
    
    if not cluster:
        raise HTTPException(status_code=404, detail=f"Cluster with ID '{cluster_id}' not found")

    try:
        # Create Kubernetes configuration using cluster data
        from kubernetes.client import Configuration, ApiClient
        
        configuration = Configuration()
        configuration.host = cluster.server_url
        configuration.api_key = {"authorization": f"Bearer {cluster.token}"}
        configuration.api_key_prefix = {"authorization": ""}
        configuration.verify_ssl = cluster.use_secure_tls
        
        # Configure TLS if needed
        if cluster.use_secure_tls and cluster.ca_data:
            import tempfile
            import base64
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.crt') as ca_file:
                try:
                    ca_content = base64.b64decode(cluster.ca_data).decode('utf-8')
                except:
                    ca_content = cluster.ca_data
                ca_file.write(ca_content)
                configuration.ssl_ca_cert = ca_file.name
        
        # Create API client and get namespaces
        api_client = ApiClient(configuration)
        v1 = client.CoreV1Api(api_client)
        
        namespace_list = v1.list_namespace()
        namespaces = [ns.metadata.name for ns in namespace_list.items]
        
        logger.info(f"Successfully retrieved {len(namespaces)} namespaces from cluster {cluster.cluster_name}")
        
        return JSONResponse(content={
            "cluster_id": cluster_id,
            "cluster_name": cluster.cluster_name,
            "namespaces": namespaces
        }, status_code=200)
    
    except client.rest.ApiException as e:
        logger.error(f"Kubernetes API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching namespaces: {e.reason}")
    except Exception as e:
        logger.error(f"Error fetching namespaces: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching namespaces: {str(e)}")


@cluster_router.get("/cluster/{cluster_name}/credentials",
                   summary="Get Cluster Credentials by Name", 
                   description="Returns server URL and token for a specific cluster by name")
async def get_cluster_credentials(
    cluster_name: str,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get cluster credentials (server URL and token) by cluster name.
    
    - Verifies that the user has access to the specified cluster
    - Returns server URL, token, and other connection details
    - Used for direct cluster access without kubeconfig files
    
    Parameters:
        cluster_name: The name of the cluster to get credentials for
    
    Returns:
        JSONResponse: Cluster connection details including server URL and token
        
    Raises:
        HTTPException: 404 error if cluster not found or user doesn't have access
        HTTPException: 403 error if user doesn't own the cluster
    """
    logger.info(f"Cluster credentials request for cluster '{cluster_name}' by user {current_user['id']}")
    
    try:
        # Find the cluster by name and user
        cluster = session.exec(
            select(ClusterConfig).where(
                ClusterConfig.cluster_name == cluster_name,
                ClusterConfig.user_id == current_user["id"]
            )
        ).first()
        
        if not cluster:
            logger.warning(f"Cluster '{cluster_name}' not found for user {current_user['id']}")
            raise HTTPException(
                status_code=404, 
                detail=f"Cluster '{cluster_name}' not found or you don't have access to it"
            )
        
        # Prepare response with cluster credentials
        credentials_response = {
            "cluster_id": cluster.id,
            "cluster_name": cluster.cluster_name,
            "server_url": cluster.server_url,
            "token": cluster.token,
            "context_name": cluster.context_name,
            "provider_name": cluster.provider_name,
            "use_secure_tls": cluster.use_secure_tls,
            "tls_config": {
                "ca_data": cluster.ca_data,
                "tls_cert": cluster.tls_cert,
                "tls_key": cluster.tls_key
            } if cluster.use_secure_tls else None,
            "is_operator_installed": cluster.is_operator_installed,
            "tags": cluster.tags,
            "created_at": cluster.created_at.isoformat() if cluster.created_at else None,
            "updated_at": cluster.updated_at.isoformat() if cluster.updated_at else None
        }
        
        # Log successful access
        logger.info(f"User {current_user['id']} successfully retrieved credentials for cluster '{cluster_name}'")
        
        # Publish cluster access event
        try:
            publish_message("cluster_events", {
                "event_type": "cluster_credentials_accessed",
                "cluster_id": cluster.id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": cluster_name,
                "server_url": cluster.server_url,
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish cluster access event: {str(queue_error)}")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Cluster credentials retrieved successfully",
            "cluster": credentials_response
        }, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving cluster credentials for '{cluster_name}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving cluster credentials: {str(e)}")


    """
    Retrieves all namespaces from the active Kubernetes cluster.
    
    - Gets the active cluster configuration from database
    - Uses the cluster's server URL and token dynamically
    - Returns list of namespace names
    
    Returns:
        JSONResponse: List of namespace names
        
    Raises:
        HTTPException: 404 error if active cluster not found
        HTTPException: 500 error if namespace retrieval fails
    """
    print(f"🔍 DEBUG: get_namespaces called for user: {current_user}")
    
    # Get active cluster configuration dynamically from database
    try:
        active_cluster = session.exec(
            select(ClusterConfig).where(
                ClusterConfig.user_id == current_user["id"],
                ClusterConfig.active == True
            )
        ).first()
        
        
        if not active_cluster:
            logger.error(f"No active cluster found for user {current_user['id']}")
            raise HTTPException(status_code=404, detail="No active cluster configuration found")
        
        print(f"🔍 DEBUG: Active cluster found:")
        print(f"  - ID: {active_cluster.id}")
        print(f"  - Name: {active_cluster.cluster_name}")
        print(f"  - Server URL: {active_cluster.server_url}")
        print(f"  - Use Secure TLS: {active_cluster.use_secure_tls}")
        print(f"  - Has Token: {'Yes' if active_cluster.token else 'No'}")
        print(f"  - Token Length: {len(active_cluster.token) if active_cluster.token else 0}")
        
    except Exception as db_error:
        logger.error(f"Database error while getting active cluster: {str(db_error)}")
        raise HTTPException(status_code=500, detail="Error retrieving cluster configuration")
    
    logger.info(f"Getting namespaces for user {current_user['id']} from cluster {active_cluster.cluster_name}")

    try:
        # Create Kubernetes configuration using dynamic values
        from kubernetes.client import Configuration, ApiClient
        
        configuration = Configuration()
        
        # Use the server URL exactly as stored in database (don't modify it)
        configuration.host = active_cluster.server_url
        
        # Dynamic token from database
        token = active_cluster.token
        if not token:
            raise HTTPException(status_code=400, detail="No token found for active cluster")
        
        # Set authentication using dynamic token (same as static version)
        configuration.api_key = {"authorization": f"Bearer {token}"}
        configuration.api_key_prefix = {"authorization": ""}
        
        # Configure TLS based on cluster settings
        if active_cluster.use_secure_tls:
            configuration.verify_ssl = True
            
            # Handle CA certificate if provided
            if active_cluster.ca_data:
                import tempfile
                import base64
                
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.crt') as ca_file:
                    try:
                        # Try to decode base64 CA data
                        ca_content = base64.b64decode(active_cluster.ca_data).decode('utf-8')
                    except:
                        # If not base64, use as is
                        ca_content = active_cluster.ca_data
                    ca_file.write(ca_content)
                    configuration.ssl_ca_cert = ca_file.name
            
            # Handle client certificates if provided
            if active_cluster.tls_cert and active_cluster.tls_key:
                import tempfile
                import base64
                
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.crt') as cert_file:
                    try:
                        cert_content = base64.b64decode(active_cluster.tls_cert).decode('utf-8')
                    except:
                        cert_content = active_cluster.tls_cert
                    cert_file.write(cert_content)
                    configuration.cert_file = cert_file.name
                
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.key') as key_file:
                    try:
                        key_content = base64.b64decode(active_cluster.tls_key).decode('utf-8')
                    except:
                        key_content = active_cluster.tls_key
                    key_file.write(key_content)
                    configuration.key_file = key_file.name
        else:
            # Use insecure connection (same as static version)
            configuration.verify_ssl = False
        
        print(f"🔍 DEBUG: Dynamic Configuration:")
        print(f"  - Host: {configuration.host}")
        print(f"  - Token Preview: {token[:30] + '...' if len(token) > 30 else token}")
        print(f"  - Verify SSL: {configuration.verify_ssl}")
        
        logger.info(f"Configuration created with host: {configuration.host}")
        logger.info(f"Token format: Bearer {token[:20]}...")
        
        # Create API client
        api_client = ApiClient(configuration)
        v1 = client.CoreV1Api(api_client)
        
        logger.info("Attempting to list namespaces...")
        print(f"🔍 DEBUG: About to call v1.list_namespace() with URL: {configuration.host}")
        
        # List namespaces
        namespace_list = v1.list_namespace()
        namespaces = [ns.metadata.name for ns in namespace_list.items]
        
        print(f"🔍 DEBUG: Successfully retrieved namespaces:")
        print(f"  - Count: {len(namespaces)}")
        print(f"  - Names: {namespaces}")
        
        logger.info(f"Successfully retrieved {len(namespaces)} namespaces: {namespaces}")
        
        # Publish success event (optional - remove if causing issues)
        try:
            publish_message("cluster_events", {
                "event_type": "namespaces_retrieved",
                "cluster_id": active_cluster.id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": active_cluster.cluster_name,
                "namespace_count": len(namespaces),
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish success message to queue: {str(queue_error)}")
        
        # Return the same format as your static version
        return JSONResponse(content={"namespaces": namespaces}, status_code=200)
    
    except client.rest.ApiException as e:
        print(f"🔍 DEBUG: Kubernetes API Exception:")
        print(f"  - Status: {e.status}")
        print(f"  - Reason: {e.reason}")
        print(f"  - Body: {e.body}")
        
        logger.error(f"Kubernetes API error: Status={e.status}, Reason={e.reason}")
        logger.error(f"Response body: {e.body}")
        
        # Publish failure event (optional - remove if causing issues)
        try:
            publish_message("cluster_events", {
                "event_type": "namespaces_retrieval_failed",
                "cluster_id": active_cluster.id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": active_cluster.cluster_name,
                "error": f"API Error: {e.status} - {e.reason}",
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish error message to queue: {str(queue_error)}")
        
        raise HTTPException(status_code=500, detail=f"Error fetching namespaces: {e.reason}")
    
    except Exception as e:
        print(f"🔍 DEBUG: General Exception:")
        print(f"  - Type: {type(e).__name__}")
        print(f"  - Message: {str(e)}")
        
        logger.error(f"Error fetching namespaces: {str(e)}")
        
        # Publish failure event (optional - remove if causing issues)
        try:
            publish_message("cluster_events", {
                "event_type": "namespaces_retrieval_failed",
                "cluster_id": active_cluster.id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": active_cluster.cluster_name,
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish error message to queue: {str(queue_error)}")
        
        raise HTTPException(status_code=500, detail=f"Error fetching namespaces: {str(e)}")



def analyze_pods(api, namespace=None):
    """Analyze Pods for common issues"""
    results = []
    
    # Get pods from all namespaces or specific namespace
    if namespace:
        pods = api.list_namespaced_pod(namespace)
    else:
        pods = api.list_pod_for_all_namespaces()
    
    for pod in pods.items:
        pod_name = pod.metadata.name
        pod_namespace = pod.metadata.namespace
        full_name = f"{pod_namespace}/{pod_name}"
        
        # Check for pod status issues
        if pod.status.phase not in ["Running", "Succeeded"]:
            results.append({
                "kind": "Pod",
                "name": full_name,
                "error": [{
                    "Text": f"Pod is in {pod.status.phase} state",
                    "KubernetesDoc": "",
                    "Sensitive": []
                }],
                "details": "",
                "parentObject": ""
            })
        
        # Check container statuses
        if pod.status.container_statuses:
            for container in pod.status.container_statuses:
                # Check for container restarts
                if container.restart_count > 5:
                    results.append({
                        "kind": "Pod",
                        "name": full_name,
                        "error": [{
                            "Text": f"Container {container.name} has restarted {container.restart_count} times",
                            "KubernetesDoc": "",
                            "Sensitive": []
                        }],
                        "details": "",
                        "parentObject": ""
                    })
                
                # Check for container not ready
                if not container.ready and pod.status.phase == "Running":
                    results.append({
                        "kind": "Pod",
                        "name": full_name,
                        "error": [{
                            "Text": f"Container {container.name} is not ready",
                            "KubernetesDoc": "",
                            "Sensitive": []
                        }],
                        "details": "",
                        "parentObject": ""
                    })
                
                # Check for waiting containers
                if container.state.waiting:
                    results.append({
                        "kind": "Pod",
                        "name": full_name,
                        "error": [{
                            "Text": f"Container {container.name} is waiting: {container.state.waiting.reason} - {container.state.waiting.message or ''}",
                            "KubernetesDoc": "",
                            "Sensitive": []
                        }],
                        "details": "",
                        "parentObject": ""
                    })
                
                # Check for terminated containers with error
                if container.state.terminated and container.state.terminated.exit_code != 0:
                    results.append({
                        "kind": "Pod",
                        "name": full_name,
                        "error": [{
                            "Text": f"Container {container.name} terminated with error: {container.state.terminated.reason} - {container.state.terminated.message or ''}",
                            "KubernetesDoc": "",
                            "Sensitive": []
                        }],
                        "details": "",
                        "parentObject": ""
                    })
        
        # Check for pod conditions
        if pod.status.conditions:
            for condition in pod.status.conditions:
                if condition.type == "Ready" and condition.status != "True" and pod.status.phase == "Running":
                    results.append({
                        "kind": "Pod",
                        "name": full_name,
                        "error": [{
                            "Text": f"Pod is not ready: {condition.reason} - {condition.message}",
                            "KubernetesDoc": "",
                            "Sensitive": []
                        }],
                        "details": "",
                        "parentObject": ""
                    })
        
        # Check for events related to this pod (would require additional API call)
        # This would be a more comprehensive approach but requires more API calls
    
    return results

def analyze_deployments(api, namespace=None):
    """Analyze Deployments for common issues"""
    results = []
    
    # Get deployments from all namespaces or specific namespace
    if namespace:
        deployments = api.list_namespaced_deployment(namespace)
    else:
        deployments = api.list_deployment_for_all_namespaces()
    
    for deployment in deployments.items:
        deployment_name = deployment.metadata.name
        deployment_namespace = deployment.metadata.namespace
        full_name = f"{deployment_namespace}/{deployment_name}"
        
        # Check if deployment is available
        if deployment.status.available_replicas is None or deployment.status.available_replicas < deployment.spec.replicas:
            available = deployment.status.available_replicas or 0
            results.append({
                "kind": "Deployment",
                "name": full_name,
                "error": [{
                    "Text": f"Deployment has {available}/{deployment.spec.replicas} available replicas",
                    "KubernetesDoc": "",
                    "Sensitive": []
                }],
                "details": "",
                "parentObject": ""
            })
        
        # Check for deployment conditions
        if deployment.status.conditions:
            for condition in deployment.status.conditions:
                if condition.type == "Available" and condition.status != "True":
                    results.append({
                        "kind": "Deployment",
                        "name": full_name,
                        "error": [{
                            "Text": f"Deployment is not available: {condition.reason} - {condition.message}",
                            "KubernetesDoc": "",
                            "Sensitive": []
                        }],
                        "details": "",
                        "parentObject": ""
                    })
                if condition.type == "Progressing" and condition.status != "True":
                    results.append({
                        "kind": "Deployment",
                        "name": full_name,
                        "error": [{
                            "Text": f"Deployment is not progressing: {condition.reason} - {condition.message}",
                            "KubernetesDoc": "",
                            "Sensitive": []
                        }],
                        "details": "",
                        "parentObject": ""
                    })
    
    return results

def analyze_services(api, namespace=None):
    """Analyze Services for common issues"""
    results = []
    
    # Get services from all namespaces or specific namespace
    if namespace:
        services = api.list_namespaced_service(namespace)
    else:
        services = api.list_service_for_all_namespaces()
    
    for service in services.items:
        service_name = service.metadata.name
        service_namespace = service.metadata.namespace
        full_name = f"{service_namespace}/{service_name}"
        
        # Check if service has no endpoints (would require additional API call)
        try:
            if namespace:
                endpoints = api.read_namespaced_endpoints(service_name, service_namespace)
            else:
                # This is a workaround since there's no direct method to get endpoints by service name across namespaces
                endpoints = api.read_namespaced_endpoints(service_name, service_namespace)
            
            if not endpoints.subsets or not any(subset.addresses for subset in endpoints.subsets):
                results.append({
                    "kind": "Service",
                    "name": full_name,
                    "error": [{
                        "Text": "Service has no endpoints (no pods match the selector)",
                        "KubernetesDoc": "",
                        "Sensitive": []
                    }],
                    "details": "",
                    "parentObject": ""
                })
        except client.rest.ApiException:
            # Endpoint might not exist
            results.append({
                "kind": "Service",
                "name": full_name,
                "error": [{
                    "Text": "Service has no associated endpoints",
                    "KubernetesDoc": "",
                    "Sensitive": []
                }],
                "details": "",
                "parentObject": ""
            })
    
    return results

def analyze_secrets(api, namespace=None):
    """Analyze Secrets for common issues"""
    results = []
    
    # Get secrets from all namespaces or specific namespace
    if namespace:
        secrets = api.list_namespaced_secret(namespace)
        # For cross-checking with pods
        pods = api.list_namespaced_pod(namespace)
    else:
        secrets = api.list_secret_for_all_namespaces()
        # For cross-checking with pods
        pods = api.list_pod_for_all_namespaces()
    
    # Create a map of secret references from pods
    secret_references = {}
    for pod in pods.items:
        pod_name = f"{pod.metadata.namespace}/{pod.metadata.name}"
        
        # Check volume-mounted secrets
        if pod.spec.volumes:
            for volume in pod.spec.volumes:
                if volume.secret and volume.secret.secret_name:
                    secret_name = volume.secret.secret_name
                    secret_key = f"{pod.metadata.namespace}/{secret_name}"
                    if secret_key not in secret_references:
                        secret_references[secret_key] = []
                    secret_references[secret_key].append({
                        "resource": pod_name,
                        "kind": "Pod",
                        "usage": f"volume mount: {volume.name}"
                    })
        
        # Check environment variables from secrets
        if pod.spec.containers:
            for container in pod.spec.containers:
                if container.env:
                    for env in container.env:
                        if env.value_from and env.value_from.secret_key_ref:
                            secret_name = env.value_from.secret_key_ref.name
                            secret_key = f"{pod.metadata.namespace}/{secret_name}"
                            key_name = env.value_from.secret_key_ref.key
                            if secret_key not in secret_references:
                                secret_references[secret_key] = []
                            secret_references[secret_key].append({
                                "resource": pod_name,
                                "kind": "Pod",
                                "usage": f"env var: {env.name}, key: {key_name}"
                            })
    
    # Process each secret
    for secret in secrets.items:
        secret_name = secret.metadata.name
        secret_namespace = secret.metadata.namespace
        full_name = f"{secret_namespace}/{secret_name}"
        secret_key = full_name
        
        # Skip default service account tokens
        if secret.type == "kubernetes.io/service-account-token" and secret_name.startswith("default-token"):
            continue
        
        # 1. Check for empty secrets
        if not secret.data or len(secret.data) == 0:
            results.append({
                "kind": "Secret",
                "name": full_name,
                "error": [{
                    "Text": "Secret has no data",
                    "KubernetesDoc": "",
                    "Sensitive": []
                }],
                "details": "",
                "parentObject": ""
            })
            continue  # Skip further checks for empty secrets
        
        # 2. Check for malformed base64 data
        try:
            for key, value in secret.data.items():
                # The kubernetes client already decodes base64, so we don't need to check this
                pass
        except Exception as e:
            results.append({
                "kind": "Secret",
                "name": full_name,
                "error": [{
                    "Text": f"Secret contains malformed data: {str(e)}",
                    "KubernetesDoc": "",
                    "Sensitive": []
                }],
                "details": "",
                "parentObject": ""
            })
        
        # 3. Check for referenced but non-existent secrets is handled by the pod analysis
        
        # 4. Check for TLS certificate expiration
        if secret.type == "kubernetes.io/tls" and "tls.crt" in secret.data:
            try:
                import base64
                import datetime
                import cryptography.x509
                from cryptography.hazmat.backends import default_backend
                
                cert_data = base64.b64decode(secret.data["tls.crt"])
                cert = cryptography.x509.load_pem_x509_certificate(cert_data, default_backend())
                
                # Check if certificate is expired
                if cert.not_valid_after_utc < datetime.datetime.now(timezone.utc):
                    results.append({
                        "kind": "Secret",
                        "name": full_name,
                        "error": [{
                            "Text": f"TLS certificate in Secret has expired on {cert.not_valid_after_utc.strftime('%Y-%m-%d')}",
                            "KubernetesDoc": "",
                            "Sensitive": []
                        }],
                        "details": "",
                        "parentObject": ""
                    })
                
                # Check if certificate is about to expire (within 30 days)
                days_to_expiry = (cert.not_valid_after_utc - datetime.datetime.now(timezone.utc)).days
                if 0 < days_to_expiry < 30:
                    results.append({
                        "kind": "Secret",
                        "name": full_name,
                        "error": [{
                            "Text": f"TLS certificate in Secret will expire in {days_to_expiry} days (on {cert.not_valid_after_utc.strftime('%Y-%m-%d')})",
                            "KubernetesDoc": "",
                            "Sensitive": []
                        }],
                        "details": "",
                        "parentObject": ""
                    })
            except Exception:
                # Skip certificate validation if we can't parse it
                pass
        
        # 5. Check for missing required keys based on secret type
        if secret.type == "kubernetes.io/dockerconfigjson" and ".dockerconfigjson" not in secret.data:
            results.append({
                "kind": "Secret",
                "name": full_name,
                "error": [{
                    "Text": "Docker config secret is missing required '.dockerconfigjson' key",
                    "KubernetesDoc": "",
                    "Sensitive": []
                }],
                "details": "",
                "parentObject": ""
            })
        elif secret.type == "kubernetes.io/tls":
            missing_keys = []
            for required_key in ["tls.crt", "tls.key"]:
                if required_key not in secret.data:
                    missing_keys.append(required_key)
            
            if missing_keys:
                results.append({
                    "kind": "Secret",
                    "name": full_name,
                    "error": [{
                        "Text": f"TLS secret is missing required keys: {', '.join(missing_keys)}",
                        "KubernetesDoc": "",
                        "Sensitive": []
                    }],
                    "details": "",
                    "parentObject": ""
                })
        
        # 6. Check for unused secrets
        if secret_key not in secret_references:
            results.append({
                "kind": "Secret",
                "name": full_name,
                "error": [{
                    "Text": "Secret is not used by any pods in the cluster",
                    "KubernetesDoc": "",
                    "Sensitive": []
                }],
                "details": "",
                "parentObject": ""
            })
        
        # 7. Check for incorrect type (requires cross-checking with pods)
        if secret_key in secret_references:
            for reference in secret_references[secret_key]:
                # Check for docker registry secrets used as regular secrets
                if secret.type == "kubernetes.io/dockerconfigjson" and "env var" in reference["usage"]:
                    results.append({
                        "kind": "Secret",
                        "name": full_name,
                        "error": [{
                            "Text": f"Secret has type 'kubernetes.io/dockerconfigjson' but is used as environment variable in {reference['kind']} {reference['resource']}",
                            "KubernetesDoc": "",
                            "Sensitive": []
                        }],
                        "details": "",
                        "parentObject": reference["resource"]
                    })
        
        # 8. Insufficient permissions check would require RBAC analysis, which is complex
        
        # 9. Check for oversized secrets (1MB limit is recommended)
        total_size = 0
        for _, value in secret.data.items():
            # The size in bytes of the base64 decoded value
            total_size += len(value) if value else 0
        
        if total_size > 1000000:  # 1MB in bytes
            size_mb = round(total_size / 1000000, 2)
            results.append({
                "kind": "Secret",
                "name": full_name,
                "error": [{
                    "Text": f"Secret size ({size_mb}MB) exceeds recommended limit of 1MB",
                    "KubernetesDoc": "",
                    "Sensitive": []
                }],
                "details": "",
                "parentObject": ""
            })
    
    return results


def analyze_storage_classes(api):
    """Analyze StorageClasses for common issues"""
    results = []
    
    storage_classes = api.list_storage_class()
    
    # Check if there are no storage classes
    if not storage_classes.items:
        results.append({
            "kind": "StorageClass",
            "name": "N/A",
            "error": [{
                "Text": "No StorageClasses found in the cluster",
                "KubernetesDoc": "",
                "Sensitive": []
            }],
            "details": "",
            "parentObject": ""
        })
    
    # Check for default storage class
    default_storage_class = False
    for sc in storage_classes.items:
        if sc.metadata.annotations and "storageclass.kubernetes.io/is-default-class" in sc.metadata.annotations:
            if sc.metadata.annotations["storageclass.kubernetes.io/is-default-class"].lower() == "true":
                default_storage_class = True
                break
    
    if not default_storage_class and storage_classes.items:
        results.append({
            "kind": "StorageClass",
            "name": "N/A",
            "error": [{
                "Text": "No default StorageClass found in the cluster",
                "KubernetesDoc": "",
                "Sensitive": []
            }],
            "details": "",
            "parentObject": ""
        })
    
    return results

def analyze_ingress(api_networking, api_core, namespace=None):
    """Analyze Ingress resources for common issues"""
    results = []
    
    # Get ingress from all namespaces or specific namespace
    if namespace:
        ingresses = api_networking.list_namespaced_ingress(namespace)
    else:
        ingresses = api_networking.list_ingress_for_all_namespaces()
    
    for ingress in ingresses.items:
        ingress_name = ingress.metadata.name
        ingress_namespace = ingress.metadata.namespace
        full_name = f"{ingress_namespace}/{ingress_name}"
        
        # Check for TLS configuration
        if not ingress.spec.tls:
            results.append({
                "kind": "Ingress",
                "name": full_name,
                "error": [{
                    "Text": "Ingress does not have TLS configured",
                    "KubernetesDoc": "",
                    "Sensitive": []
                }],
                "details": "",
                "parentObject": ""
            })
        
        # Check for rules
        if not ingress.spec.rules:
            results.append({
                "kind": "Ingress",
                "name": full_name,
                "error": [{
                    "Text": "Ingress does not have any rules defined",
                    "KubernetesDoc": "",
                    "Sensitive": []
                }],
                "details": "",
                "parentObject": ""
            })
        
        # Check for backend services (would require additional API calls to verify if services exist)
        for rule in ingress.spec.rules or []:
            if rule.http and rule.http.paths:
                for path in rule.http.paths:
                    if path.backend and path.backend.service:
                        service_name = path.backend.service.name
                        service_port = path.backend.service.port.number if path.backend.service.port.number else path.backend.service.port.name
                        
                        # Check if service exists (would require additional API call)
                        try:
                            # Use the CoreV1Api to check for services
                            api_core.read_namespaced_service(service_name, ingress_namespace)
                        except client.rest.ApiException as e:
                            if e.status == 404:
                                results.append({
                                    "kind": "Ingress",
                                    "name": full_name,
                                    "error": [{
                                        "Text": f"Ingress references non-existent service: {service_name}",
                                        "KubernetesDoc": "",
                                        "Sensitive": []
                                    }],
                                    "details": "",
                                    "parentObject": ""
                                })
    
    return results


def analyze_pvcs(api, namespace=None):
    """Analyze PersistentVolumeClaims for common issues"""
    results = []
    
    # Get PVCs from all namespaces or specific namespace
    if namespace:
        pvcs = api.list_namespaced_persistent_volume_claim(namespace)
    else:
        pvcs = api.list_persistent_volume_claim_for_all_namespaces()
    
    for pvc in pvcs.items:
        pvc_name = pvc.metadata.name
        pvc_namespace = pvc.metadata.namespace
        full_name = f"{pvc_namespace}/{pvc_name}"
        
        # Check for pending PVCs
        if pvc.status.phase == "Pending":
            results.append({
                "kind": "PersistentVolumeClaim",
                "name": full_name,
                "error": [{
                    "Text": "PersistentVolumeClaim is in Pending state",
                    "KubernetesDoc": "",
                    "Sensitive": []
                }],
                "details": "",
                "parentObject": ""
            })
        
        # Check for PVCs with access modes that might cause issues
        if pvc.spec.access_modes and "ReadWriteMany" in pvc.spec.access_modes:
            # ReadWriteMany is not supported by all storage providers
            # This is just a warning, not necessarily an error
            if pvc.spec.storage_class_name:
                results.append({
                    "kind": "PersistentVolumeClaim",
                    "name": full_name,
                    "error": [{
                        "Text": f"PVC uses ReadWriteMany access mode with storage class {pvc.spec.storage_class_name}, verify that this is supported",
                        "KubernetesDoc": "",
                        "Sensitive": []
                    }],
                    "details": "",
                    "parentObject": ""
                })
        
        # Check for bound PVCs with no pods using them (would require additional API calls)
        # This is a more advanced check that would require listing pods and checking their volumes
    
    return results

def check_pod_events(api, pod_namespace, pod_name):
    """Check for recent events related to a pod"""
    field_selector = f"involvedObject.name={pod_name},involvedObject.namespace={pod_namespace},involvedObject.kind=Pod"
    events = api.list_event_for_all_namespaces(field_selector=field_selector)
    
    issues = []
    for event in events.items:
        # Focus on Warning events
        if event.type == "Warning":
            # Check if event is recent (last 15 minutes)
            event_time = event.last_timestamp or event.event_time
            if event_time:
                event_time = event_time.replace(tzinfo=None)
                if (datetime.datetime.utcnow() - event_time).total_seconds() < 900:  # 15 minutes in seconds
                    issues.append({
                        "Text": f"{event.reason}: {event.message}",
                        "KubernetesDoc": "",
                        "Sensitive": []
                    })
    
    return issues

def analyze_pod_with_events(api, namespace=None):
    """Enhanced pod analysis that includes event information"""
    results = []
    
    # Get pods from all namespaces or specific namespace
    if namespace:
        pods = api.list_namespaced_pod(namespace)
    else:
        pods = api.list_pod_for_all_namespaces()
    
    for pod in pods.items:
        pod_name = pod.metadata.name
        pod_namespace = pod.metadata.namespace
        full_name = f"{pod_namespace}/{pod_name}"
        
        # Basic pod status checks (similar to analyze_pods)
        issues = []
        
        # Check for pod status issues
        if pod.status.phase not in ["Running", "Succeeded"]:
            issues.append({
                "Text": f"Pod is in {pod.status.phase} state",
                "KubernetesDoc": "",
                "Sensitive": []
            })
        
        # Check container statuses
        if pod.status.container_statuses:
            for container in pod.status.container_statuses:
                # Check for container restarts
                if container.restart_count > 5:
                    issues.append({
                        "Text": f"Container {container.name} has restarted {container.restart_count} times",
                        "KubernetesDoc": "",
                        "Sensitive": []
                    })
                
                # Check for container not ready
                if not container.ready and pod.status.phase == "Running":
                    issues.append({
                        "Text": f"Container {container.name} is not ready",
                        "KubernetesDoc": "",
                        "Sensitive": []
                    })
                
                # Check for waiting containers
                if container.state.waiting:
                    issues.append({
                        "Text": f"Container {container.name} is waiting: {container.state.waiting.reason} - {container.state.waiting.message or ''}",
                        "KubernetesDoc": "",
                        "Sensitive": []
                    })
                
                # Check for terminated containers with error
                if container.state.terminated and container.state.terminated.exit_code != 0:
                    issues.append({
                        "Text": f"Container {container.name} terminated with error: {container.state.terminated.reason} - {container.state.terminated.message or ''}",
                        "KubernetesDoc": "",
                        "Sensitive": []
                    })
        
        # Check for pod conditions
        if pod.status.conditions:
            for condition in pod.status.conditions:
                if condition.type == "Ready" and condition.status != "True" and pod.status.phase == "Running":
                    issues.append({
                        "Text": f"Pod is not ready: {condition.reason} - {condition.message}",
                        "KubernetesDoc": "",
                        "Sensitive": []
                    })
        
        # Get pod events
        event_issues = check_pod_events(api, pod_namespace, pod_name)
        issues.extend(event_issues)
        
        # Only add to results if there are issues
        if issues:
            results.append({
                "kind": "Pod",
                "name": full_name,
                "error": issues,
                "details": "",
                "parentObject": ""
            })
    
    return results


# **************************** llm analyze solution ****************************

import asyncio
from functools import partial
async def run_k8s_analysis_async(cluster, resource_types: List[str], namespace: str, user_id: str) -> List[Dict]:
    """Run Kubernetes analysis in background thread with better error handling"""
    
    def _run_k8s_analysis_sync():
        """Synchronous K8s analysis - runs in executor"""
        try:
            # CHANGED: Use server_url and token from cluster object instead of active_cluster
            configuration = Configuration()
            
            configuration.host = cluster.server_url
            configuration.api_key = {"authorization": f"Bearer {cluster.token}"}
            configuration.api_key_prefix = {"authorization": ""}
            configuration.verify_ssl = cluster.use_secure_tls
            print(f"Using server_url: {cluster.server_url}")
            
            # Create API client with configuration
            api_client = ApiClient(configuration)
        
            # Quick connectivity test
            core_v1 = client.CoreV1Api(api_client)
            try:
                # Test with a simple API call first
                core_v1.get_api_resources()
                logger.info(f"Cluster connectivity verified for user {user_id}")
            except client.rest.ApiException as e:
                if "cluster agent disconnected" in str(e):
                    raise Exception(f"Cluster agent disconnected. Please check your cluster connectivity.")
                elif e.status == 401:
                    raise Exception(f"Authentication failed. Please check your cluster credentials.")
                elif e.status == 403:
                    raise Exception(f"Access denied. Please check your cluster permissions.")
                else:
                    raise Exception(f"Cluster connectivity issue: {str(e)}")
            
            # Initialize API clients with the same api_client
            apps_v1 = client.AppsV1Api(api_client)
            networking_v1 = client.NetworkingV1Api(api_client)
            storage_v1 = client.StorageV1Api(api_client)
            
            # Run analysis with timeout protection
            flat_results = []
            for resource_type in resource_types:
                try:
                    resource_type = resource_type.lower()
                    logger.info(f"Analyzing {resource_type} for user {user_id}")
                    
                    if resource_type == "pods":
                        flat_results.extend(analyze_pods(core_v1, namespace))
                    elif resource_type == "deployments":
                        flat_results.extend(analyze_deployments(apps_v1, namespace))
                    elif resource_type == "services":
                        flat_results.extend(analyze_services(core_v1, namespace))
                    elif resource_type == "secrets":
                        flat_results.extend(analyze_secrets(core_v1, namespace))
                    elif resource_type == "storageclasses":
                        flat_results.extend(analyze_storage_classes(storage_v1))
                    elif resource_type == "ingress":
                        flat_results.extend(analyze_ingress(networking_v1, core_v1, namespace))
                    elif resource_type == "pvc":
                        flat_results.extend(analyze_pvcs(core_v1, namespace))
                        
                except Exception as e:
                    logger.error(f"Failed to analyze {resource_type} for user {user_id}: {str(e)}")
                    # Continue with other resource types
                    continue
            
            return flat_results
            
        except Exception as e:
            logger.error(f"K8s analysis failed for user {user_id}: {str(e)}")
            raise
    
    # Run in background thread with timeout
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _run_k8s_analysis_sync),
            timeout=600  # 10 minutes timeout
        )
    except asyncio.TimeoutError:
        raise Exception(f"Analysis timed out after 600 seconds for user {user_id}")


async def generate_solutions_concurrently(resource_errors: Dict, llm_service: K8sLLMService, cluster, user_id: str) -> List[Dict]:
    """Generate solutions for multiple resources concurrently"""
    
    async def generate_single_solution(resource_key: str, resource_data: Dict) -> Dict:
        """Generate solution for a single resource"""
        try:
            # Combine all error texts for this resource
            error_texts = []
            for error in resource_data["errors"]:
                if isinstance(error, dict) and "Text" in error:
                    error_texts.append(error["Text"])
                elif isinstance(error, str):
                    error_texts.append(error)
            
            combined_error_text = "; ".join(error_texts)
            
            # Generate solution using LLM (now async)
            solution = await llm_service.generate_solution(
                error_text=combined_error_text,
                kind=resource_data["kind"],
                name=resource_data["name"],
                namespace=resource_data["namespace"],
                context={
                    "cluster_name": cluster.cluster_name,  # CHANGED: Use cluster object instead of active_cluster
                    "total_errors": len(error_texts)
                },
                user_id=user_id
            )
            
            # Validate solution structure
            if not isinstance(solution, dict):
                raise ValueError("Invalid solution format")
            
            # Ensure required fields exist with defaults
            solution.setdefault("solution_summary", "Solution generated")
            solution.setdefault("detailed_solution", "Please check the remediation steps")
            solution.setdefault("remediation_steps", [])
            solution.setdefault("confidence_score", 0.5)
            solution.setdefault("estimated_time_mins", 30)
            solution.setdefault("additional_notes", "")
            
            return {
                "problem": {
                    "kind": resource_data["kind"],
                    "name": resource_data["name"],
                    "namespace": resource_data["namespace"],
                    "errors": resource_data["errors"],
                    "details": resource_data["details"],
                    "parentObject": resource_data["parentObject"]
                },
                "solution": solution
            }
            
        except Exception as e:
            logger.error(f"Failed to generate solution for {resource_key} (user {user_id}): {str(e)}")
            # Return fallback solution
            return {
                "problem": {
                    "kind": resource_data["kind"],
                    "name": resource_data["name"],
                    "namespace": resource_data["namespace"],
                    "errors": resource_data["errors"],
                    "details": resource_data["details"],
                    "parentObject": resource_data["parentObject"]
                },
                "solution": {
                    "solution_summary": "Manual investigation required",
                    "detailed_solution": f"Unable to generate automated solution. Error: {combined_error_text}",
                    "remediation_steps": [
                        {
                            "step_id": 1,
                            "action_type": "MANUAL_CHECK",
                            "description": "Investigate the issue manually",
                            "command": f"kubectl describe {resource_data['kind'].lower()} {resource_data['name']} -n {resource_data['namespace']}" if resource_data['namespace'] else f"kubectl describe {resource_data['kind'].lower()} {resource_data['name']}",
                            "expected_outcome": "Get detailed information about the resource"
                        }
                    ],
                    "confidence_score": 0.3,
                    "estimated_time_mins": 30,
                    "additional_notes": f"LLM generation failed: {str(e)}"
                }
            }
    
    # Create tasks for concurrent execution
    tasks = []
    for resource_key, resource_data in resource_errors.items():
        task = generate_single_solution(resource_key, resource_data)
        tasks.append(task)
    
    # Execute all solution generations concurrently
    logger.info(f"Generating {len(tasks)} solutions concurrently for user {user_id}")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out any exceptions and return valid results
    valid_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Task failed for user {user_id}: {result}")
        else:
            valid_results.append(result)
    
    return valid_results

#api 4 - analyze_k8s_with_solutions
@cluster_router.post("/analyze-k8s-with-solutions/{cluster_id}",
                       summary="Analyze Kubernetes Resources with AI Solutions", 
                       description="Analyzes Kubernetes resources from specified cluster and provides AI-generated solutions for each problem")
async def analyze_k8s_with_solutions(
    cluster_id: int,  # CHANGED: Now requires cluster_id parameter
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user),
    namespace: str = Query(None, description="Namespace to analyze"),
    resource_types: List[str] = Query(
        ["pods", "deployments", "services", "secrets", "storageclasses", "ingress", "pvc"],
        description="Resource types to analyze"
    )
):
    """
    Analyzes Kubernetes resources from specified cluster and provides AI-generated solutions for each problem.
    Now works with specific cluster ID instead of active cluster concept.
    """
    user_id = current_user.get("id", "unknown")
    logger.info(f"Starting K8s analysis with solutions for user {user_id} on cluster {cluster_id}")
    print(f"*************** --Starting K8s analysis with solutions for user {user_id} on cluster {cluster_id}")
    
    # Check if LLM is enabled
    if not settings.LLM_ENABLED:
        raise HTTPException(
            status_code=400, 
            detail="LLM functionality is disabled. Please enable it in settings to use AI solutions."
        )
    
    # CHANGED: Get the specified cluster instead of active cluster
    cluster = session.exec(
        select(ClusterConfig).where(
            ClusterConfig.id == cluster_id,
            ClusterConfig.user_id == current_user["id"]
        )
    ).first()
    
    if not cluster:
        raise HTTPException(
            status_code=404, 
            detail=f"Cluster with ID '{cluster_id}' not found or you don't have access to it"
        )
    
    print(f"Using cluster: {cluster.cluster_name} (ID: {cluster.id})")
    
    try:
        # CHANGED: Run K8s analysis with specified cluster instead of active cluster
        flat_results = await run_k8s_analysis_async(cluster, resource_types, namespace, user_id)
        
        # Initialize LLM service
        try:
            llm_service = K8sLLMService()
        except Exception as e:
            logger.error(f"Failed to initialize LLM service for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to initialize LLM service: {str(e)}"
            )
        
        # Group errors by resource to avoid duplicate solutions (keep existing logic)
        resource_errors = {}
        
        for result in flat_results:
            # Extract namespace from the name field (format: "namespace/name")
            name_parts = result["name"].split("/", 1)
            
            if len(name_parts) == 2:
                result_namespace, resource_name = name_parts
                if result_namespace == "N/A":
                    result_namespace = ""
            else:
                result_namespace = ""
                resource_name = result["name"]
            
            # Create a unique key for each resource
            resource_key = f"{result['kind']}/{result_namespace}/{resource_name}"
            
            if resource_key not in resource_errors:
                resource_errors[resource_key] = {
                    "kind": result["kind"],
                    "name": resource_name,
                    "namespace": result_namespace,
                    "errors": [],
                    "details": result.get("details", ""),
                    "parentObject": result.get("parentObject", "")
                }
            
            # Add all errors for this resource
            if isinstance(result["error"], list):
                resource_errors[resource_key]["errors"].extend(result["error"])
            else:
                resource_errors[resource_key]["errors"].append(result["error"])
        
        # Generate solutions concurrently for all resources
        problems_with_solutions = await generate_solutions_concurrently(
            resource_errors, llm_service, cluster, user_id
        )
        
        # CHANGED: Publish analysis event with cluster_id instead of kubeconfig_id
        publish_message("cluster_events", {
            "event_type": "k8s_analysis_with_solutions_performed",
            "cluster_id": cluster.id,
            "user_id": user_id,
            "username": current_user.get("username", "unknown"),
            "cluster_name": cluster.cluster_name,
            "resource_types": resource_types,
            "namespace": namespace or "all",
            "problem_count": len(problems_with_solutions),
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        logger.info(f"Analysis completed for user {user_id} with {len(problems_with_solutions)} problems")
        
        return JSONResponse(content={
            "cluster_id": cluster.id,  # CHANGED: Added cluster_id to response
            "cluster_name": cluster.cluster_name,
            "server_url": cluster.server_url,  # CHANGED: Added server_url to response
            "provider_name": cluster.provider_name,  # CHANGED: Added provider_name to response
            "namespace": namespace or "all",
            "analyzed_resource_types": resource_types,
            "total_problems": len(problems_with_solutions),
            "problems_with_solutions": problems_with_solutions
        }, status_code=200)
    
    except client.rest.ApiException as e:
        logger.error(f"Kubernetes API error for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Kubernetes API error: {str(e)}")
    except Exception as e:
        logger.error(f"Error analyzing Kubernetes resources with solutions for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing Kubernetes resources with solutions: {str(e)}")


#api 5 - execute kubectl command directly
@cluster_router.post("/execute-kubectl-direct/{cluster_id}",
                       summary="Execute Kubectl Command Directly", 
                       description="Execute kubectl command using cluster credentials directly")
async def execute_kubectl_command_direct(
    cluster_id: int,
    command_data: dict,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Execute kubectl command using cluster credentials directly without temporary kubeconfig.
    
    Parameters:
        cluster_id: The ID of the cluster to execute command on
        command_data: Dictionary containing the command to execute
    
    Returns:
        JSONResponse: Command execution results
    """
    # Get specified cluster
    cluster = session.exec(
        select(ClusterConfig).where(
            ClusterConfig.id == cluster_id,
            ClusterConfig.user_id == current_user["id"]
        )
    ).first()
    
    if not cluster:
        raise HTTPException(
            status_code=404, 
            detail=f"Cluster with ID '{cluster_id}' not found or you don't have access to it"
        )

    command = command_data.get("command", "")
    if not command:
        raise HTTPException(status_code=400, detail="Command is required")

    try:
        import subprocess
        
        # Prepare environment variables for kubectl
        env = dict(os.environ)
        
        # Add cluster credentials to command if it's a kubectl command
        if command.strip().startswith("kubectl"):
            # Add server and token directly to kubectl command
            if "--server" not in command:
                command += f" --server={cluster.server_url}"
            if "--token" not in command:
                command += f" --token={cluster.token}"
            if not cluster.use_secure_tls and "--insecure-skip-tls-verify" not in command:
                command += " --insecure-skip-tls-verify=true"

        logger.info(f"Executing command on cluster {cluster.cluster_name}: {command}")

        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
            env=env
        )
        
        # Process results
        success = result.returncode == 0
        output = result.stdout.strip() if result.stdout else ""
        error = result.stderr.strip() if result.stderr else None
        
        if not output and error and success:
            output = error
            error = None
        
        if not output and not error:
            if success:
                output = "Command executed successfully (no output)"
            else:
                output = "Command failed"
                error = "No error details available"
        
        # Publish command execution event
        try:
            publish_message("cluster_events", {
                "event_type": "kubectl_command_executed",
                "cluster_id": cluster.id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": cluster.cluster_name,
                "command": command,
                "success": success,
                "return_code": result.returncode,
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish command execution event: {str(queue_error)}")
        
        return JSONResponse(content={
            "success": success,
            "output": output,
            "error": error,
            "command": command,
            "return_code": result.returncode,
            "cluster_info": {
                "cluster_id": cluster.id,
                "cluster_name": cluster.cluster_name,
                "server_url": cluster.server_url,
                "provider_name": cluster.provider_name
            },
            "executed_at": datetime.datetime.now().isoformat(),
            "execution_method": "direct"
        }, status_code=200)
        
    except subprocess.TimeoutExpired:
        return JSONResponse(content={
            "success": False,
            "output": "",
            "error": "Command timed out after 300 seconds",
            "command": command,
            "return_code": -1,
            "cluster_info": {
                "cluster_id": cluster.id,
                "cluster_name": cluster.cluster_name,
                "server_url": cluster.server_url,
                "provider_name": cluster.provider_name
            },
            "executed_at": datetime.datetime.now().isoformat(),
            "execution_method": "direct"
        }, status_code=200)
    except Exception as e:
        logger.error(f"Error executing kubectl command on cluster {cluster_id}: {str(e)}")
        return JSONResponse(content={
            "success": False,
            "output": "",
            "error": str(e),
            "command": command,
            "return_code": -1,
            "cluster_info": {
                "cluster_id": cluster.id,
                "cluster_name": cluster.cluster_name,
                "server_url": cluster.server_url,
                "provider_name": cluster.provider_name
            } if cluster else None,
            "executed_at": datetime.datetime.now().isoformat(),
            "execution_method": "direct"
        }, status_code=200)


# ******************************** Prometheus api ********************************

  
PROMETHEUS_URL = "http://10.0.34.142:9090"

@cluster_router.get("/metrics/resource-usage")
async def get_user_cluster_resource_usage(
    username: str = Query(...),
    metric: str = Query(..., enum=["cpu", "memory"]),
    namespace: str = Query("default"),
    duration: int = Query(3600),
    step: int = Query(300),
):
    end = int(time.time())
    start = end - duration

    # Build PromQL query
    if metric == "cpu":
        promql = f'rate(container_cpu_usage_seconds_total{{username="{username}", namespace="{namespace}", container!=""}}[5m])'
    elif metric == "memory":
        promql = f'kube_pod_container_resource_limits{{username="{username}", container!="", resource="{metric}"}}'
        # promql = f'container_memory_usage_bytes{{username="{username}", namespace="{namespace}", container!=""}}'
        # kube_pod_container_resource_limits{{username="{username}", container!="", resource="{metric}"}}

    params = {
        "query": promql,
        "start": start,
        "end": end,
        "step": step
    }

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{PROMETHEUS_URL}/api/v1/query_range", params=params)
        r.raise_for_status()
        data = r.json()

    # Group values by timestamp across all clusters
    aggregated_usage = defaultdict(list)

    for series in data["data"]["result"]:
        for ts, val in series["values"]:
            try:
                aggregated_usage[int(ts)].append(float(val))
            except ValueError:
                continue

    # Aggregate and average across clusters per timestamp
    result = []
    for ts in sorted(aggregated_usage.keys()):
        usage_values = aggregated_usage[ts]
        average_usage = sum(usage_values) / len(usage_values) if usage_values else 0
        result.append({
            "time": time.strftime('%H:%M', time.localtime(ts)),
            "usage": average_usage
        })

    return {"data": result}


def get_nodes_status_all_clusters():
    query = 'kube_node_status_condition{condition="Ready"}'
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})
    result = response.json().get("data", {}).get("result", [])

    cluster_status = {}
    total_ready = 0
    total_not_ready = 0

    for item in result:
        metric = item.get("metric", {})
        cluster = metric.get("cluster", "unknown")
        status = metric.get("status")

        if cluster not in cluster_status:
            cluster_status[cluster] = {
                "ready": 0,
                "not_ready": 0
            }

        if status == "true":
            cluster_status[cluster]["ready"] += 1
            total_ready += 1
        elif status == "false":
            cluster_status[cluster]["not_ready"] += 1
            total_not_ready += 1

    for cluster in cluster_status:
        stats = cluster_status[cluster]
        stats["total"] = stats["ready"] + stats["not_ready"]

    return {
        "clusters": cluster_status,
        "totals": {
            "ready": total_ready,
            "not_ready": total_not_ready,
            "total": total_ready + total_not_ready
        }
    }

@cluster_router.get("/nodes/status/all-clusters")
def all_clusters_node_health():
    data = get_nodes_status_all_clusters()
    return JSONResponse(content=data)



def prometheus_query(query: str):
    url = f"{PROMETHEUS_URL}/api/v1/query"
    response = httpx.get(url, params={"query": query})
    data = response.json()
    return data.get("data", {}).get("result", [])

@cluster_router.get("/security")
async def get_security(username: str):
    severities = ["Critical", "High", "Medium", "Low"]
    vulnerabilities = {}

    # Step 1: Get counts for each severity using username
    for severity in severities:
        query = (
            f'sum(trivy_image_vulnerabilities{{severity="{severity}", username="{username}"}})'
        )
        result = prometheus_query(query)
        count = int(float(result[0]["value"][1])) if result else 0
        vulnerabilities[severity.lower()] = count

    # Step 2: Get detailed vulnerabilities by username
    issues_query = (
        f'sum(trivy_image_vulnerabilities{{username="{username}"}}) '
        f'by (namespace, image_registry, image_repository, image_tag, severity) > 0'
    )
    result = prometheus_query(issues_query)

    # Step 3: Top 1 per severity
    severity_groups = {s.lower(): [] for s in severities}
    for item in result:
        metric = item["metric"]
        severity = metric.get("severity", "").lower()
        if severity in severity_groups:
            severity_groups[severity].append(item)

    issues = []
    issue_id = 1
    for severity in severities:
        group = severity_groups[severity.lower()]
        if group:
            top = sorted(group, key=lambda x: int(float(x["value"][1])), reverse=True)[0]
            metric = top["metric"]
            image_repo = metric.get("image_repository", "unknown")
            image_tag = metric.get("image_tag", "latest")
            component = f"{image_repo}:{image_tag}"
            count = int(float(top["value"][1]))

            issues.append({
                "id": issue_id,
                "severity": severity.lower(),
                "name": "CVE-XXXX-YYYY",
                "component": component,
                "description": f"Detected {count} vulnerability(ies)"
            })
            issue_id += 1

    return {
        "lastScan": "unknown",
        "vulnerabilities": vulnerabilities,
        "issues": issues
    }



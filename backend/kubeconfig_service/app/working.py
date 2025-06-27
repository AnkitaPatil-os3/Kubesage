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

cluster_router = APIRouter()

def get_active_cluster(session: Session, user_id: int) -> ClusterConfig:
    """Get the active cluster configuration for a user"""
    active_cluster = session.exec(
        select(ClusterConfig).where(
            ClusterConfig.user_id == user_id,
            ClusterConfig.active == True
        )
    ).first()
    
    if not active_cluster:
        raise HTTPException(status_code=404, detail="No active cluster configuration found")
    
    return active_cluster

def execute_command(command: str):
    """Execute a shell command and return the result"""
    logger.debug(f"Executing command: {command}")
    try:
        args = shlex.split(command)
        result = subprocess.run(args, check=True, capture_output=True, text=True)
        
        try:
            output = json.loads(result.stdout)
            return output
        except json.JSONDecodeError:
            return {"stdout": result.stdout}
    except subprocess.CalledProcessError as e:
        logger.error(f"Command execution failed: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"Command execution failed: {e.stderr}")
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

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
@cluster_router.get("/clusters", response_model=ClusterConfigList,
                   summary="List Clusters", 
                   description="Returns a list of all onboarded clusters for the current user")
async def list_clusters(
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Lists all onboarded clusters for the current user.
    
    Returns:
        ClusterConfigList: List of cluster configuration records
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
                active=cluster.active,
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

@cluster_router.put("/activate-cluster/{cluster_id}", 
                   summary="Activate Cluster", 
                   description="Sets a specific cluster as the active one for the user")
async def activate_cluster(
    cluster_id: int,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
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
@cluster_router.get("/namespaces",
                   summary="Get Kubernetes Namespaces", 
                   description="Retrieves all namespaces from the active Kubernetes cluster")
async def get_namespaces(
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
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

@cluster_router.post("/install-operator",
                    summary="Install K8sGPT Operator", 
                    description="Installs the K8sGPT operator on the active Kubernetes cluster")
async def install_operator(
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Installs the K8sGPT operator on the active Kubernetes cluster.
    """
    active_cluster = get_active_cluster(session, current_user["id"])
    
    try:
        # Create temporary kubeconfig for helm operations
        kubeconfig_content = {
            "apiVersion": "v1",
            "kind": "Config",
            "clusters": [{
                "name": active_cluster.cluster_name,
                "cluster": {
                    "server": active_cluster.server_url,
                    "insecure-skip-tls-verify": not active_cluster.use_secure_tls
                }
            }],
            "users": [{
                "name": f"{active_cluster.cluster_name}-user",
                "user": {
                    "token": active_cluster.token
                }
            }],
            "contexts": [{
                "name": active_cluster.cluster_name,
                "context": {
                    "cluster": active_cluster.cluster_name,
                    "user": f"{active_cluster.cluster_name}-user"
                }
            }],
            "current-context": active_cluster.cluster_name
        }
        
        # Add TLS configuration if enabled
        if active_cluster.use_secure_tls and active_cluster.ca_data:
            kubeconfig_content["clusters"][0]["cluster"]["certificate-authority-data"] = active_cluster.ca_data
            kubeconfig_content["clusters"][0]["cluster"].pop("insecure-skip-tls-verify", None)
        
        # Create temporary kubeconfig file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            yaml.dump(kubeconfig_content, temp_file)
            temp_kubeconfig_path = temp_file.name
        
        commands = [
            f"helm repo add k8sgpt https://charts.k8sgpt.ai/ --kubeconfig {temp_kubeconfig_path}",
            f"helm repo update --kubeconfig {temp_kubeconfig_path}",
            f"helm install release k8sgpt/k8sgpt-operator -n k8sgpt-operator-system --create-namespace --kubeconfig {temp_kubeconfig_path}"
        ]
        
        results = []
        success = True
        error_message = ""
        
        for command in commands:
            try:
                result = execute_command(command)
                results.append({"command": command, "result": result})
            except HTTPException as e:
                error_message = str(e.detail)
                results.append({"command": command, "error": error_message})
                success = False
                break
        
        # Clean up temporary file
        if os.path.exists(temp_kubeconfig_path):
            os.unlink(temp_kubeconfig_path)
        
        if success:
            # Update operator installation status in DB
            active_cluster.is_operator_installed = True
            session.add(active_cluster)
            session.commit()
            
            logger.info(f"User {current_user['id']} installed operator on cluster {active_cluster.cluster_name}")
            
            # Publish operator installed event
            try:
                publish_message("cluster_events", {
                    "event_type": "operator_installed",
                    "cluster_id": active_cluster.id,
                    "user_id": current_user["id"],
                    "username": current_user.get("username", "unknown"),
                    "cluster_name": active_cluster.cluster_name,
                    "success": True,
                    "timestamp": datetime.datetime.now().isoformat()
                })
            except Exception as queue_error:
                logger.warning(f"Failed to publish message to queue: {str(queue_error)}")
            
            return JSONResponse(
                content={"results": results, "operator_installed": True, "message": "Operator installed successfully"},
                status_code=200
            )
        else:
            # Publish operator installation failed event
            try:
                publish_message("cluster_events", {
                    "event_type": "operator_installation_failed",
                    "cluster_id": active_cluster.id,
                    "user_id": current_user["id"],
                    "username": current_user.get("username", "unknown"),
                    "cluster_name": active_cluster.cluster_name,
                    "error": error_message,
                    "timestamp": datetime.datetime.now().isoformat()
                })
            except Exception as queue_error:
                logger.warning(f"Failed to publish message to queue: {str(queue_error)}")
            
            return JSONResponse(
                content={
                    "results": results,
                    "operator_installed": False,
                    "message": f"Operator installation failed: {error_message}"
                },
                status_code=400
            )
    
    except Exception as e:
        logger.error(f"Error installing operator: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error installing operator: {str(e)}")

@cluster_router.post("/uninstall-operator",
                    summary="Uninstall K8sGPT Operator", 
                    description="Uninstalls the K8sGPT operator from the active Kubernetes cluster")
async def uninstall_operator(
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Uninstalls the K8sGPT operator from the active Kubernetes cluster.
    """
    active_cluster = get_active_cluster(session, current_user["id"])
    
    results = []
    success = True
    error_message = ""
    
    try:
        # Load the kubeconfig
        configuration = Configuration()
        configuration.host = active_cluster.server_url
        configuration.api_key = {"authorization": f"Bearer {active_cluster.token}"}
        configuration.api_key_prefix = {"authorization": "Bearer"}
        configuration.verify_ssl = active_cluster.use_secure_tls
        
        # Create API clients
        api_client = ApiClient(configuration)
        core_v1_api = client.CoreV1Api(api_client)
        
        # Step 1: Uninstall Helm release using subprocess
        try:
            # Create temporary kubeconfig for helm operations
            kubeconfig_content = {
                "apiVersion": "v1",
                "kind": "Config",
                "clusters": [{
                    "name": active_cluster.cluster_name,
                    "cluster": {
                        "server": active_cluster.server_url,
                        "insecure-skip-tls-verify": not active_cluster.use_secure_tls
                    }
                }],
                "users": [{
                    "name": f"{active_cluster.cluster_name}-user",
                    "user": {
                        "token": active_cluster.token
                    }
                }],
                "contexts": [{
                    "name": active_cluster.cluster_name,
                    "context": {
                        "cluster": active_cluster.cluster_name,
                        "user": f"{active_cluster.cluster_name}-user"
                    }
                }],
                "current-context": active_cluster.cluster_name
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
                yaml.dump(kubeconfig_content, temp_file)
                temp_kubeconfig_path = temp_file.name
            
            helm_cmd = ["helm", "uninstall", "release", "-n", "k8sgpt-operator-system", "--kubeconfig", temp_kubeconfig_path]
            helm_result = subprocess.run(helm_cmd, capture_output=True, text=True, check=True)
            results.append({
                "operation": "Helm uninstall",
                "success": True,
                "output": helm_result.stdout
            })
            
            # Clean up temporary file
            if os.path.exists(temp_kubeconfig_path):
                os.unlink(temp_kubeconfig_path)
                
        except subprocess.CalledProcessError as e:
            # Check if the error is because the release doesn't exist
            if "release: not found" in e.stderr:
                results.append({
                    "operation": "Helm uninstall",
                    "success": True,
                    "output": "Release not found (already uninstalled)"
                })
            else:
                error_message = f"Helm uninstall failed: {e.stderr}"
                results.append({
                    "operation": "Helm uninstall",
                    "success": False,
                    "error": error_message
                })
                success = False
        
        # Step 2: Delete the namespace using Kubernetes client
        if success:
            try:
                # Check if namespace exists first
                try:
                    core_v1_api.read_namespace(name="k8sgpt-operator-system")
                    namespace_exists = True
                except client.rest.ApiException as e:
                    if e.status == 404:
                        namespace_exists = False
                    else:
                        raise
                
                if namespace_exists:
                    # Delete the namespace
                    core_v1_api.delete_namespace(name="k8sgpt-operator-system")
                    results.append({
                        "operation": "Delete namespace",
                        "success": True,
                        "output": "Namespace k8sgpt-operator-system deleted"
                    })
                else:
                    results.append({
                        "operation": "Delete namespace",
                        "success": True,
                        "output": "Namespace k8sgpt-operator-system not found (already deleted)"
                    })
            except client.rest.ApiException as e:
                error_message = f"Failed to delete namespace: {str(e)}"
                results.append({
                    "operation": "Delete namespace",
                    "success": False,
                    "error": error_message
                })
                success = False
        
        if success:
            # Update operator installation status in DB
            active_cluster.is_operator_installed = False
            session.add(active_cluster)
            session.commit()
            
            logger.info(f"User {current_user['id']} uninstalled operator from cluster {active_cluster.cluster_name}")
            
            # Publish operator uninstalled event
            try:
                publish_message("cluster_events", {
                    "event_type": "operator_uninstalled",
                    "cluster_id": active_cluster.id,
                    "user_id": current_user["id"],
                    "username": current_user.get("username", "unknown"),
                    "cluster_name": active_cluster.cluster_name,
                    "success": True,
                    "timestamp": datetime.datetime.now().isoformat()
                })
            except Exception as queue_error:
                logger.warning(f"Failed to publish message to queue: {str(queue_error)}")
            
            return JSONResponse(
                content={
                    "results": results,
                    "operator_uninstalled": True,
                    "message": "Operator uninstalled successfully"
                },
                status_code=200
            )
        else:
            # Publish operator uninstallation failed event
            try:
                publish_message("cluster_events", {
                    "event_type": "operator_uninstallation_failed",
                    "cluster_id": active_cluster.id,
                    "user_id": current_user["id"],
                    "username": current_user.get("username", "unknown"),
                    "cluster_name": active_cluster.cluster_name,
                    "error": error_message,
                    "timestamp": datetime.datetime.now().isoformat()
                })
            except Exception as queue_error:
                logger.warning(f"Failed to publish message to queue: {str(queue_error)}")
            
            return JSONResponse(
                content={
                    "results": results,
                    "operator_uninstalled": False,
                    "message": f"Failed to uninstall operator: {error_message}"
                },
                status_code=400
            )
    
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error uninstalling operator: {error_message}")
        
        # Publish operator uninstallation failed event
        try:
            publish_message("cluster_events", {
                "event_type": "operator_uninstallation_failed",
                "cluster_id": active_cluster.id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                                "cluster_name": active_cluster.cluster_name,
                "error": error_message,
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish message to queue: {str(queue_error)}")
        
        return JSONResponse(
            content={
                "results": [{"operation": "Uninstall operator", "success": False, "error": error_message}],
                "operator_uninstalled": False,
                "message": f"Error uninstalling operator: {error_message}"
            },
            status_code=500
        )

@cluster_router.post("/analyze",
                    summary="Analyze Kubernetes Cluster", 
                    description="Runs K8sGPT analysis on the active Kubernetes cluster")
async def analyze(
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user),
    anonymize: bool = Query(False, description="Anonymize data before sending it to the AI backend"),
    backend: str = Query(None, description="Backend AI provider"),
    custom_analysis: bool = Query(False, description="Enable custom analyzers"),
    custom_headers: List[str] = Query(None, description="Custom Headers, <key>:<value>"),
    explain: bool = Query(False, description="Explain the problem"),
    filter: List[str] = Query(None, description="Filter for these analyzers"),
    interactive: bool = Query(False, description="Enable interactive mode"),
    language: str = Query("english", description="Language to use for AI"),
    max_concurrency: int = Query(10, description="Maximum number of concurrent requests"),
    namespace: str = Query(None, description="Namespace to analyze"),
    no_cache: bool = Query(False, description="Do not use cached data"),
    output: str = Query("text", description="Output format (text, json)"),
    selector: str = Query(None, description="Label selector"),
    with_doc: bool = Query(False, description="Give me the official documentation of the involved field"),
    config: str = Query(None, description="Default config file"),
    kubecontext: str = Query(None, description="Kubernetes context to use")
):
    """
    Runs K8sGPT analysis on the active Kubernetes cluster.
    """
    # Get the active cluster
    active_cluster = get_active_cluster(session, current_user["id"])
    
    try:
        # Create temporary kubeconfig for k8sgpt operations
        kubeconfig_content = {
            "apiVersion": "v1",
            "kind": "Config",
            "clusters": [{
                "name": active_cluster.cluster_name,
                "cluster": {
                    "server": active_cluster.server_url,
                    "insecure-skip-tls-verify": not active_cluster.use_secure_tls
                }
            }],
            "users": [{
                "name": f"{active_cluster.cluster_name}-user",
                "user": {
                    "token": active_cluster.token
                }
            }],
            "contexts": [{
                "name": active_cluster.cluster_name,
                "context": {
                    "cluster": active_cluster.cluster_name,
                    "user": f"{active_cluster.cluster_name}-user"
                }
            }],
            "current-context": active_cluster.cluster_name
        }
        
        # Add TLS configuration if enabled
        if active_cluster.use_secure_tls and active_cluster.ca_data:
            kubeconfig_content["clusters"][0]["cluster"]["certificate-authority-data"] = active_cluster.ca_data
            kubeconfig_content["clusters"][0]["cluster"].pop("insecure-skip-tls-verify", None)
        
        # Create temporary kubeconfig file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            yaml.dump(kubeconfig_content, temp_file)
            temp_kubeconfig_path = temp_file.name
        
        # Build k8sgpt command
        command = "k8sgpt analyze"
        if anonymize:
            command += " --anonymize"
        if backend:
            command += f" --backend {backend}"
        if custom_analysis:
            command += " --custom-analysis"
        if custom_headers:
            for header in custom_headers:
                command += f" --custom-headers {header}"
        if explain:
            command += " --explain"
        if filter:
            for f in filter:
                command += f" --filter {f}"
        if interactive:
            command += " --interactive"
        if language != "english":
            command += f" --language {language}"
        if max_concurrency != 10:
            command += f" --max-concurrency {max_concurrency}"
        if namespace:
            command += f" --namespace {namespace}"
        if no_cache:
            command += " --no-cache"
        if output != "text":
            command += f" --output {output}"
        if selector:
            command += f" --selector {selector}"
        if with_doc:
            command += " --with-doc"
        if config:
            command += f" --config {config}"
        if kubecontext:
            command += f" --kubecontext {kubecontext}"
        
        # Add the temporary kubeconfig path
        command += f" --kubeconfig {temp_kubeconfig_path}"

        logger.info(f"Executing k8sgpt command: {command}")
        
        try:
            result = execute_command(command + " --output=json")
            
            # Clean up temporary file
            if os.path.exists(temp_kubeconfig_path):
                os.unlink(temp_kubeconfig_path)
            
            return JSONResponse(content=result, status_code=200)
        except HTTPException as e:
            # Clean up temporary file
            if os.path.exists(temp_kubeconfig_path):
                os.unlink(temp_kubeconfig_path)
            return JSONResponse(content={"error": str(e.detail)}, status_code=e.status_code)
    
    except Exception as e:
        logger.error(f"Error in k8sgpt analysis: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@cluster_router.post("/analyze-k8s",
                    summary="Analyze Kubernetes Resources", 
                    description="Analyzes Kubernetes resources using the Kubernetes client library")
async def analyze_k8s(
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user),
    namespace: str = Query(None, description="Namespace to analyze"),
    resource_types: List[str] = Query(
        ["pods", "deployments", "services", "secrets", "storageclasses", "ingress", "pvc"],
        description="Resource types to analyze"
    )
):
    """
    Analyzes Kubernetes resources using the Kubernetes client library.
    """
    # Get the active cluster
    active_cluster = get_active_cluster(session, current_user["id"])
    
    try:
        # Create Kubernetes configuration
        configuration = Configuration()
        configuration.host = active_cluster.server_url
        configuration.api_key = {"authorization": f"Bearer {active_cluster.token}"}
        configuration.api_key_prefix = {"authorization": "Bearer"}
        configuration.verify_ssl = active_cluster.use_secure_tls
        
        # Initialize API clients
        api_client = ApiClient(configuration)
        core_v1 = client.CoreV1Api(api_client)
        apps_v1 = client.AppsV1Api(api_client)
        networking_v1 = client.NetworkingV1Api(api_client)
        storage_v1 = client.StorageV1Api(api_client)
        
        # Initialize results list
        flat_results = []
        
        # Analyze resources based on resource_types
        for resource_type in resource_types:
            resource_type = resource_type.lower()
            
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
        
        # Modify the results to separate namespace and name
        modified_results = []
        
        for result in flat_results:
            # Extract namespace from the name field (format: "namespace/name")
            name_parts = result["name"].split("/", 1)
            
            if len(name_parts) == 2:
                result_namespace, resource_name = name_parts
                
                # Create a new result with separate namespace field
                modified_result = result.copy()
                modified_result["namespace"] = result_namespace
                modified_result["name"] = resource_name
                
                # For cluster-scoped resources
                if result_namespace == "N/A":
                    modified_result["namespace"] = ""
                
                modified_results.append(modified_result)
            else:
                # If the name doesn't have a namespace part, keep it as is
                modified_result = result.copy()
                modified_result["namespace"] = ""
                modified_results.append(modified_result)
        
        # Publish analysis event
        try:
            publish_message("cluster_events", {
                "event_type": "k8s_analysis_performed",
                "cluster_id": active_cluster.id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": active_cluster.cluster_name,
                "resource_types": resource_types,
                "namespace": namespace or "all",
                "issue_count": len(flat_results),
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish message to queue: {str(queue_error)}")
        
        return JSONResponse(content=modified_results, status_code=200)
    
    except client.rest.ApiException as e:
        logger.error(f"Kubernetes API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Kubernetes API error: {str(e)}")
    except Exception as e:
        logger.error(f"Error analyzing Kubernetes resources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing Kubernetes resources: {str(e)}")

# Analysis helper functions
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
        
        # Check if service has no endpoints
        try:
            endpoints = api.read_namespaced_endpoints(service_name, service_namespace)
            
            if not endpoints.subsets or not any(subset.addresses for subset in endpoints.subsets if subset.addresses):
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
        pods = api.list_namespaced_pod(namespace)
    else:
        secrets = api.list_secret_for_all_namespaces()
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
        
        # Check for empty secrets
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
            continue
        
        # Check for TLS certificate expiration
        if secret.type == "kubernetes.io/tls" and "tls.crt" in secret.data:
            try:
                import cryptography.x509
                from cryptography.hazmat.backends import default_backend
                from datetime import timezone
                
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
        
        # Check for missing required keys based on secret type
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
        
        # Check for unused secrets
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
        
        # Check for backend services
        for rule in ingress.spec.rules or []:
            if rule.http and rule.http.paths:
                for path in rule.http.paths:
                    if path.backend and path.backend.service:
                        service_name = path.backend.service.name
                        
                        # Check if service exists
                        try:
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
    
    return results

@cluster_router.post("/analyze-k8s-with-solutions",
                    summary="Analyze Kubernetes Resources with AI Solutions", 
                    description="Analyzes Kubernetes resources and provides AI-generated solutions for each problem")
async def analyze_k8s_with_solutions(
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user),
    namespace: str = Query(None, description="Namespace to analyze"),
    resource_types: List[str] = Query(
        ["pods", "deployments", "services", "secrets", "storageclasses", "ingress", "pvc"],
        description="Resource types to analyze"
    )
):
    """
    Analyzes Kubernetes resources and provides AI-generated solutions for each problem.
    """
    # Check if LLM is enabled
    if not settings.LLM_ENABLED:
        raise HTTPException(
            status_code=400, 
            detail="LLM functionality is disabled. Please enable it in settings to use AI solutions."
        )
    
    # Get the active cluster
    active_cluster = get_active_cluster(session, current_user["id"])
    print(active_cluster)
    
    try:
        # Create Kubernetes configuration using active cluster data
        configuration = Configuration()
        configuration.host = active_cluster.server_url  # Dynamic server URL
        configuration.api_key = {"authorization": f"Bearer {active_cluster.token}"}  # Dynamic token
        configuration.api_key_prefix = {"authorization": ""}  # Fixed authentication
        configuration.verify_ssl = active_cluster.use_secure_tls  # Dynamic TLS setting
        print(configuration.host)
        print(configuration.api_key)
        
        # Initialize API clients
        api_client = ApiClient(configuration)
        core_v1 = client.CoreV1Api(api_client)
        apps_v1 = client.AppsV1Api(api_client)
        networking_v1 = client.NetworkingV1Api(api_client)
        storage_v1 = client.StorageV1Api(api_client)
        
        # Initialize results list
        flat_results = []
        
        # Analyze resources based on resource_types
        for resource_type in resource_types:
            resource_type = resource_type.lower()
            
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
        
        # Process results and generate solutions using LLM
        problems_with_solutions = []
        
        # Initialize LLM service with error handling
        llm_service = None
        try:
            from app.llm_service import K8sLLMService
            llm_service = K8sLLMService()
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {str(e)}")
            # Continue without LLM service - we'll use fallback solutions
            logger.warning("Continuing without LLM service - using fallback solutions")
        
        # Group errors by resource to avoid duplicate solutions
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
        
        # Generate solutions for each resource's problems
        for resource_key, resource_data in resource_errors.items():
            # Combine all error texts for this resource
            error_texts = []
            for error in resource_data["errors"]:
                if isinstance(error, dict) and "Text" in error:
                    error_texts.append(error["Text"])
                elif isinstance(error, str):
                    error_texts.append(error)
            
            combined_error_text = "; ".join(error_texts)
            
            # Generate solution using LLM (if available)
            solution = None
            if llm_service:
                try:
                    solution = llm_service.generate_solution(
                        error_text=combined_error_text,
                        kind=resource_data["kind"],
                        name=resource_data["name"],
                        namespace=resource_data["namespace"],
                        context={
                            "cluster_name": active_cluster.cluster_name,
                            "total_errors": len(error_texts)
                        }
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
                    
                except Exception as e:
                    logger.error(f"Failed to generate solution for {resource_key}: {str(e)}")
                    solution = None
            
            # Use fallback solution if LLM failed or unavailable
            if not solution:
                solution = {
                    "solution_summary": "Manual investigation required",
                    "detailed_solution": f"Issue detected: {combined_error_text}. Please investigate manually.",
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
                    "additional_notes": "LLM service unavailable - manual solution provided"
                }
            
            # Create the problem-solution pair
            problem_with_solution = {
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
            
            problems_with_solutions.append(problem_with_solution)
        
        # Publish analysis event
        try:
            publish_message("cluster_events", {
                "event_type": "k8s_analysis_with_solutions_performed",
                "cluster_id": active_cluster.id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": active_cluster.cluster_name,
                "resource_types": resource_types,
                "namespace": namespace or "all",
                "problem_count": len(problems_with_solutions),
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as queue_error:
            logger.warning(f"Failed to publish message to queue: {str(queue_error)}")
        
        return JSONResponse(content={
            "cluster_name": active_cluster.cluster_name,
            "namespace": namespace or "all",
            "analyzed_resource_types": resource_types,
            "total_problems": len(problems_with_solutions),
            "problems_with_solutions": problems_with_solutions,
            "llm_service_available": llm_service is not None
        }, status_code=200)
    
    except client.rest.ApiException as e:
        logger.error(f"Kubernetes API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Kubernetes API error: {str(e)}")
    except Exception as e:
        logger.error(f"Error analyzing Kubernetes resources with solutions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing Kubernetes resources with solutions: {str(e)}")

# Backward compatibility routes - these will redirect to the new cluster endpoints
kubeconfig_router = APIRouter()


@kubeconfig_router.post("/upload", response_model=ClusterConfigResponse, status_code=201,
                       summary="Upload Kubeconfig (Deprecated)", 
                       description="Deprecated: Use /cluster/onboard-cluster instead")
async def upload_kubeconfig_deprecated(
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Deprecated endpoint. Use /cluster/onboard-cluster instead.
    """
    raise HTTPException(
        status_code=410, 
        detail="This endpoint is deprecated. Please use /cluster/onboard-cluster instead."
    )

@kubeconfig_router.get("/list", response_model=ClusterConfigList,
                      summary="List Kubeconfigs (Deprecated)", 
                      description="Deprecated: Use /cluster/clusters instead")
async def list_kubeconfigs_deprecated(
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Deprecated endpoint. Use /cluster/clusters instead.
    """
    # For backward compatibility, redirect to new endpoint
    return await list_clusters(session, current_user)

@kubeconfig_router.put("/activate/{cluster_id}", 
                      summary="Activate Kubeconfig (Deprecated)", 
                      description="Deprecated: Use /cluster/activate-cluster/{cluster_id} instead")
async def set_active_kubeconfig_deprecated(
    cluster_id: int,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Deprecated endpoint. Use /cluster/activate-cluster/{cluster_id} instead.
    """
    # For backward compatibility, redirect to new endpoint
    return await activate_cluster(cluster_id, session, current_user)

@kubeconfig_router.delete("/remove/{cluster_id}",
                         summary="Remove Kubeconfig (Deprecated)", 
                         description="Deprecated: Use /cluster/remove-cluster/{cluster_id} instead")
async def remove_kubeconfig_deprecated(
    cluster_id: int,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Deprecated endpoint. Use /cluster/remove-cluster/{cluster_id} instead.
    """
    # For backward compatibility, redirect to new endpoint
    return await remove_cluster(cluster_id, session, current_user)

# Export both routers for main app
__all__ = ["cluster_router", "kubeconfig_router"]

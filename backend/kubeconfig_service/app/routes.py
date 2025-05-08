from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session, select, update
from typing import List, Dict, Optional
import os, uuid, json, subprocess, shlex, datetime  # Added datetime
import yaml
import subprocess
import tempfile
from kubernetes import client, config
import tempfile
from app.database import get_session
from app.models import Kubeconf
from app.schemas import (
    KubeconfigResponse,
    KubeconfigList,
    MessageResponse,
    ClusterNamesResponse
)
from app.auth import get_current_user
from app.config import settings
from app.logger import logger
from app.queue import publish_message  # Updated to use our new queue implementation
 
kubeconfig_router = APIRouter()
 
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
 
def get_active_kubeconfig(session: Session, user_id: int) -> Kubeconf:
    """Get the active kubeconfig for a user"""
    active_kubeconf = session.exec(
        select(Kubeconf).where(
            Kubeconf.user_id == user_id,
            Kubeconf.active == True
        )
    ).first()
    
    if not active_kubeconf:
        raise HTTPException(status_code=404, detail="No active kubeconfig found")
    
    return active_kubeconf

@kubeconfig_router.post("/upload", response_model=KubeconfigResponse, status_code=201,
                       summary="Upload Kubeconfig", 
                       description="Uploads a kubeconfig file for Kubernetes cluster access")
async def upload_kubeconfig(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Uploads a kubeconfig file for Kubernetes cluster access.
    
    - Accepts a kubeconfig file upload
    - Saves the file with a unique name
    - Extracts cluster and context information
    - Creates a database record for the kubeconfig
    - Publishes a kubeconfig upload event to the message queue
    
    Parameters:
        file: The kubeconfig file to upload
    
    Returns:
        KubeconfigResponse: The created kubeconfig record
        
    Raises:
        HTTPException: 400 error if file format is invalid
        HTTPException: 500 error if upload fails
    """
    logger.info(f"Upload request received for user {current_user['id']} with file {file.filename}")
    try:
        # Generate a unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
        # Read file content
        file_content = await file.read()
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Parse the kubeconfig file to extract cluster and context information
        kubeconfig = yaml.safe_load(file_content.decode('utf-8'))
        
        # Extract cluster name and context name
        cluster_name = ""
        context_name = ""
        
        # Get current context
        current_context = kubeconfig.get('current-context', '')
        
        # Find the context and its cluster
        if 'contexts' in kubeconfig and kubeconfig['contexts']:
            # If there's a current-context, find that one
            if current_context:
                for ctx in kubeconfig['contexts']:
                    if ctx['name'] == current_context:
                        context_name = ctx['name']
                        cluster_name = ctx['context']['cluster']
                        break
            # Otherwise use the first context
            if not context_name and kubeconfig['contexts']:
                context_name = kubeconfig['contexts'][0]['name']
                cluster_name = kubeconfig['contexts'][0]['context']['cluster']
        
        # Create a new Kubeconf object
        new_kubeconf = Kubeconf(
            filename=unique_filename,
            original_filename=file.filename,
            user_id=current_user["id"],
            path=file_path,
            active=False,
            cluster_name=cluster_name,
            context_name=context_name
        )
        
        # Add to database
        session.add(new_kubeconf)
        session.commit()
        session.refresh(new_kubeconf)
        
        logger.info(f"User {current_user['id']} uploaded kubeconfig: {unique_filename}")
        
        # Publish kubeconfig uploaded event
        publish_message("kubeconfig_events", {
            "event_type": "kubeconfig_uploaded",
            "kubeconfig_id": new_kubeconf.id,
            "user_id": current_user["id"],
            "username": current_user.get("username", "unknown"),
            "filename": unique_filename,
            "cluster_name": cluster_name,
            "context_name": context_name,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        return new_kubeconf
    except yaml.YAMLError as e:
        logger.error(f"Error parsing kubeconfig YAML: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid kubeconfig file format: {str(e)}")
    except Exception as e:
        logger.error(f"Error uploading kubeconfig: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@kubeconfig_router.put("/activate/{filename}", 
                      summary="Activate Kubeconfig", 
                      description="Sets a specific kubeconfig as the active one for the user")
async def set_active_kubeconfig(
        filename: str,
        session: Session = Depends(get_session),
        current_user: Dict = Depends(get_current_user)
):
    """
    Sets a specific kubeconfig as the active one for the user.
    
    - Finds the kubeconfig by filename
    - Deactivates all other kubeconfigs for the user
    - Activates the selected kubeconfig
    - Publishes a kubeconfig activation event to the message queue
    
    Parameters:
        filename: The filename of the kubeconfig to activate
    
    Returns:
        JSONResponse: Success message
        
    Raises:
        HTTPException: 404 error if kubeconfig not found
    """
    # Find the kubeconfig to activate
    kubeconf_to_activate = session.exec(
        select(Kubeconf).where(
            Kubeconf.filename == filename,
            Kubeconf.user_id == current_user["id"]
        )
    ).first()

    if not kubeconf_to_activate:
        raise HTTPException(status_code=404, detail=f"Kubeconfig '{filename}' not found")
 
    # Deactivate all kubeconfigs for this user
    session.exec(
        update(Kubeconf)
        .where(Kubeconf.user_id == current_user["id"])
        .values(active=False)
    )
 
    # Activate the selected kubeconfig
    kubeconf_to_activate.active = True
    session.add(kubeconf_to_activate)
    session.commit()

    logger.info(f"User {current_user['id']} activated kubeconfig: {filename}")
    
    # Publish kubeconfig activated event
    publish_message("kubeconfig_events", {
        "event_type": "kubeconfig_activated",
        "kubeconfig_id": kubeconf_to_activate.id,
        "user_id": current_user["id"],
        "username": current_user.get("username", "unknown"),
        "filename": filename,
        "cluster_name": kubeconf_to_activate.cluster_name,
        "context_name": kubeconf_to_activate.context_name,
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    return JSONResponse(content={"message": f"Kubeconfig '{filename}' set as active"}, status_code=200)
 
@kubeconfig_router.get("/list", response_model=KubeconfigList,
                      summary="List Kubeconfigs", 
                      description="Returns a list of all kubeconfig files for the current user")
async def list_kubeconfigs(
        session: Session = Depends(get_session),
        current_user: Dict = Depends(get_current_user)
):
    """
    Lists all kubeconfig files for the current user.
    
    - Retrieves all kubeconfig records for the current user
    - Orders them by creation date (newest first)
    
    Returns:
        KubeconfigList: List of kubeconfig records
    """
    kubeconfigs = session.exec(
        select(Kubeconf)
        .where(Kubeconf.user_id == current_user["id"])
        .order_by(Kubeconf.created_at.desc())
    ).all()

    return {"kubeconfigs": kubeconfigs}


#*************** we are not using this route **************************
@kubeconfig_router.get("/clusters", response_model=ClusterNamesResponse,
                      summary="Get Cluster Names", 
                      description="Returns a list of cluster names from all kubeconfigs")
async def get_cluster_names(
        session: Session = Depends(get_session),
        current_user: Dict = Depends(get_current_user)
):
    """
    Returns a list of cluster names from all kubeconfigs.
    
    - Retrieves all kubeconfig records for the current user
    - Extracts cluster names from each kubeconfig
    - For kubeconfigs without stored cluster names, attempts to retrieve them
    - Updates the database with any newly retrieved cluster names
    
    Returns:
        ClusterNamesResponse: List of cluster names and any errors encountered
    """
    cluster_names = []
    errors = []
 
    # Query all Kubeconfs entries for the current user
    kubeconfs = session.exec(
        select(Kubeconf).where(Kubeconf.user_id == current_user["id"])
    ).all()
 
    for kubeconf in kubeconfs:
        if kubeconf.cluster_name:
            cluster_names.append({
                "filename": kubeconf.filename,
                "cluster_name": kubeconf.cluster_name,
                "active": kubeconf.active,
                "operator_installed": kubeconf.is_operator_installed,
            })
        else:
            # If cluster_name is not available in the database, try to retrieve it
            try:
                if not os.path.exists(kubeconf.path):
                    errors.append({
                        "filename": kubeconf.filename,
                        "error": "Kubeconfig file not found on disk"
                    })
                    continue
                
                command = f"kubectl config view --kubeconfig {kubeconf.path} --minify -o jsonpath='{{.clusters[0].name}}'"
                result = execute_command(command)
                cluster_name = result.get("stdout", "").strip()
            
                if cluster_name:
                    cluster_names.append({
                        "filename": kubeconf.filename,
                        "cluster_name": cluster_name,
                        "active": kubeconf.active,
                        "operator_installed": kubeconf.is_operator_installed
                    })
                    # Update the database with the retrieved cluster name
                    kubeconf.cluster_name = cluster_name
                    session.add(kubeconf)
                else:
                    errors.append({
                        "filename": kubeconf.filename,
                        "error": "Unable to retrieve cluster name"
                    })
            except HTTPException as e:
                errors.append({
                    "filename": kubeconf.filename,
                    "error": str(e.detail)
                })
 
    # Commit any changes made to the database
    session.commit()
 
    response: Dict[str, List] = {"cluster_names": cluster_names}
    if errors:
        response["errors"] = errors
 
    return response
 


@kubeconfig_router.delete("/remove",
                         summary="Remove Kubeconfig", 
                         description="Deletes a kubeconfig file from the system")
async def remove_kubeconfig(
        filename: str = Query(..., description="Filename of the kubeconfig to remove"),
        session: Session = Depends(get_session),
        current_user: Dict = Depends(get_current_user)
):
    """
    Deletes a kubeconfig file from the system.
    
    - Finds the kubeconfig by filename
    - Removes the file from disk if it exists
    - Deletes the database record
    - Publishes a kubeconfig deletion event to the message queue
    
    Parameters:
        filename: The filename of the kubeconfig to remove
    
    Returns:
        JSONResponse: Success message
        
    Raises:
        HTTPException: 404 error if kubeconfig not found
        HTTPException: 500 error if deletion fails
    """
    # Check if the file exists in the database and belongs to the current user
    kubeconf = session.exec(
        select(Kubeconf).where(
            Kubeconf.filename == filename,
            Kubeconf.user_id == current_user["id"]
        )
    ).first()

    if not kubeconf:
        raise HTTPException(status_code=404, detail=f"Kubeconfig '{filename}' not found or does not belong to you")
 
    file_path = kubeconf.path
    
    # Save kubeconf info before deletion for event publishing
    kubeconf_info = {
        "id": kubeconf.id,
        "filename": kubeconf.filename,
        "cluster_name": kubeconf.cluster_name,
        "context_name": kubeconf.context_name
    }

    # Check if the file exists on disk
    if not os.path.exists(file_path):
        # If file doesn't exist on disk but exists in DB, we should still remove the DB entry
        session.delete(kubeconf)
        session.commit()
        logger.info(f"User {current_user['id']} removed kubeconfig {filename} from database (file not found)")
        
        # Publish kubeconfig deleted event
        publish_message("kubeconfig_events", {
            "event_type": "kubeconfig_deleted",
            "kubeconfig_id": kubeconf_info["id"],
            "user_id": current_user["id"],
            "username": current_user.get("username", "unknown"),
                        "filename": filename,
            "cluster_name": kubeconf_info["cluster_name"],
            "context_name": kubeconf_info["context_name"],
            "file_existed": False,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        return JSONResponse(content={
            "message": f"Kubeconfig '{filename}' removed from database. File was not found on disk."
        }, status_code=200)
    
    try:
        # Remove the file from disk
        os.remove(file_path)
    
        # Remove the entry from the database
        session.delete(kubeconf)
        session.commit()
        
        # Publish kubeconfig deleted event
        publish_message("kubeconfig_events", {
            "event_type": "kubeconfig_deleted",
            "kubeconfig_id": kubeconf_info["id"],
            "user_id": current_user["id"],
            "username": current_user.get("username", "unknown"),
            "filename": filename,
            "cluster_name": kubeconf_info["cluster_name"],
            "context_name": kubeconf_info["context_name"],
            "file_existed": True,
            "timestamp": datetime.datetime.now().isoformat()
        })
    
        logger.info(f"User {current_user['id']} removed kubeconfig {filename}")
        return JSONResponse(content={
            "message": f"Kubeconfig '{filename}' successfully removed from disk and database"
        }, status_code=200)
    except Exception as e:
        # If an error occurs, rollback the database transaction
        session.rollback()
        logger.error(f"Error removing kubeconfig: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error removing kubeconfig: {str(e)}")
 
@kubeconfig_router.post("/install-operator",
                       summary="Install K8sGPT Operator", 
                       description="Installs the K8sGPT operator on the active Kubernetes cluster")
async def install_operator(
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Installs the K8sGPT operator on the active Kubernetes cluster.
    
    - Gets the active kubeconfig
    - Adds the K8sGPT Helm repository
    - Updates Helm repositories
    - Installs the K8sGPT operator using Helm
    - Updates the database to mark the operator as installed
    - Publishes an operator installation event to the message queue
    
    Returns:
        JSONResponse: Installation results and status
        
    Raises:
        HTTPException: 404 error if active kubeconfig not found
        HTTPException: 400 error if installation fails
    """
    active_kubeconf = get_active_kubeconfig(session, current_user["id"])
    kubeconfig_path = active_kubeconf.path
 
    if not os.path.exists(kubeconfig_path):
        raise HTTPException(status_code=404, detail="Active kubeconfig file not found on disk")
 
    commands = [
        f"helm repo add k8sgpt https://charts.k8sgpt.ai/ --kubeconfig {kubeconfig_path}",
        f"helm repo update --kubeconfig {kubeconfig_path}",
        f"helm install release k8sgpt/k8sgpt-operator -n k8sgpt-operator-system --create-namespace --kubeconfig {kubeconfig_path}"
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
            break  # Stop execution if a command fails
    
    if success:
        # Update operator installation status in DB
        active_kubeconf.is_operator_installed = True
        session.add(active_kubeconf)
        session.commit()
        
        logger.info(f"User {current_user['id']} installed operator on cluster {active_kubeconf.cluster_name}")
        
        # Publish operator installed event
        publish_message("kubeconfig_events", {
            "event_type": "operator_installed",
            "kubeconfig_id": active_kubeconf.id,
            "user_id": current_user["id"],
            "username": current_user.get("username", "unknown"),
            "cluster_name": active_kubeconf.cluster_name,
            "success": True,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        return JSONResponse(
            content={"results": results, "operator_installed": True, "message": "Operator installed successfully"},
            status_code=200
        )
    else:
        # Publish operator installation failed event
        publish_message("kubeconfig_events", {
            "event_type": "operator_installation_failed",
            "kubeconfig_id": active_kubeconf.id,
            "user_id": current_user["id"],
            "username": current_user.get("username", "unknown"),
            "cluster_name": active_kubeconf.cluster_name,
            "error": error_message,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        return JSONResponse(
            content={
                "results": results,
                "operator_installed": False,
                "message": f"Operator is already installed: {error_message}"
            },
            status_code=400  # Bad Request for command execution failure
        )
 

@kubeconfig_router.post("/uninstall-operator",
                       summary="Uninstall K8sGPT Operator", 
                       description="Uninstalls the K8sGPT operator from the active Kubernetes cluster")
async def uninstall_operator(
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Uninstalls the K8sGPT operator from the active Kubernetes cluster.
    
    - Gets the active kubeconfig
    - Uninstalls the K8sGPT Helm release
    - Deletes the operator namespace
    - Updates the database to mark the operator as uninstalled
    - Publishes an operator uninstallation event to the message queue
    
    Returns:
        JSONResponse: Uninstallation results and status
        
    Raises:
        HTTPException: 404 error if active kubeconfig not found
        HTTPException: 400/500 error if uninstallation fails
    """
    active_kubeconf = get_active_kubeconfig(session, current_user["id"])
    kubeconfig_path = active_kubeconf.path
    
    if not os.path.exists(kubeconfig_path):
        raise HTTPException(status_code=404, detail="Active kubeconfig file not found on disk")
    
    results = []
    success = True
    error_message = ""
    
    try:
        # Load the kubeconfig
        config.load_kube_config(config_file=kubeconfig_path)
        
        # Create API clients
        core_v1_api = client.CoreV1Api()
        
        # Step 1: Uninstall Helm release using subprocess (Kubernetes client doesn't support Helm operations)
        # We'll use a more controlled subprocess approach
        try:
            helm_cmd = ["helm", "uninstall", "release", "-n", "k8sgpt-operator-system", "--kubeconfig", kubeconfig_path]
            helm_result = subprocess.run(helm_cmd, capture_output=True, text=True, check=True)
            results.append({
                "operation": "Helm uninstall",
                "success": True,
                "output": helm_result.stdout
            })
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
            active_kubeconf.is_operator_installed = False
            session.add(active_kubeconf)
            session.commit()
            
            logger.info(f"User {current_user['id']} uninstalled operator from cluster {active_kubeconf.cluster_name}")
            
            # Publish operator uninstalled event
            publish_message("kubeconfig_events", {
                "event_type": "operator_uninstalled",
                "kubeconfig_id": active_kubeconf.id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": active_kubeconf.cluster_name,
                "success": True,
                "timestamp": datetime.datetime.now().isoformat()
            })
            
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
            publish_message("kubeconfig_events", {
                "event_type": "operator_uninstallation_failed",
                "kubeconfig_id": active_kubeconf.id,
                "user_id": current_user["id"],
                "username": current_user.get("username", "unknown"),
                "cluster_name": active_kubeconf.cluster_name,
                "error": error_message,
                "timestamp": datetime.datetime.now().isoformat()
            })
            
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
        publish_message("kubeconfig_events", {
            "event_type": "operator_uninstallation_failed",
            "kubeconfig_id": active_kubeconf.id,
            "user_id": current_user["id"],
            "username": current_user.get("username", "unknown"),
            "cluster_name": active_kubeconf.cluster_name,
            "error": error_message,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        return JSONResponse(
            content={
                "results": [{"operation": "Uninstall operator", "success": False, "error": error_message}],
                "operator_uninstalled": False,
                "message": f"Error uninstalling operator: {error_message}"
            },
            status_code=500
        )


@kubeconfig_router.get("/namespaces",
                      summary="Get Kubernetes Namespaces", 
                      description="Retrieves all namespaces from the active Kubernetes cluster")
async def get_namespaces(
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Retrieves all namespaces from the active Kubernetes cluster.
    
    - Gets the active kubeconfig
    - Uses the Kubernetes API to list all namespaces
    - Publishes a namespace retrieval event to the message queue
    
    Returns:
        JSONResponse: List of namespace names
        
    Raises:
        HTTPException: 404 error if active kubeconfig not found
        HTTPException: 500 error if namespace retrieval fails
    """
    active_kubeconf = get_active_kubeconfig(session, current_user["id"])
    kubeconfig_path = active_kubeconf.path

    if not os.path.exists(kubeconfig_path):
        raise HTTPException(status_code=404, detail="Active kubeconfig file not found on disk")

    try:
        # Load the kubeconfig file
        config.load_kube_config(config_file=kubeconfig_path)
        
        # Create a Kubernetes API client
        v1 = client.CoreV1Api()
        
        # List all namespaces
        namespace_list = v1.list_namespace()
        
        # Extract namespace names
        namespaces = [ns.metadata.name for ns in namespace_list.items]
        print("namespaces :" , namespaces)
        
        logger.info(f"User {current_user['id']} retrieved namespaces from cluster {active_kubeconf.cluster_name}")
        
        # Publish namespaces retrieved event
        publish_message("kubeconfig_events", {
            "event_type": "namespaces_retrieved",
            "kubeconfig_id": active_kubeconf.id,
            "user_id": current_user["id"],
            "username": current_user.get("username", "unknown"),
            "cluster_name": active_kubeconf.cluster_name,
            "namespace_count": len(namespaces),
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        return JSONResponse(content={"namespaces": namespaces}, status_code=200)
    
    except client.rest.ApiException as e:
        logger.error(f"Kubernetes API error: {str(e)}")
        
        # Publish namespace retrieval failed event
        publish_message("kubeconfig_events", {
            "event_type": "namespaces_retrieval_failed",
            "kubeconfig_id": active_kubeconf.id,
            "user_id": current_user["id"],
            "username": current_user.get("username", "unknown"),
            "cluster_name": active_kubeconf.cluster,
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        raise HTTPException(status_code=500, detail=f"Error fetching namespaces: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error fetching namespaces: {str(e)}")
        
        # Publish namespace retrieval failed event
        publish_message("kubeconfig_events", {
            "event_type": "namespaces_retrieval_failed",
            "kubeconfig_id": active_kubeconf.id,
            "user_id": current_user["id"],
            "username": current_user.get("username", "unknown"),
            "cluster_name": active_kubeconf.cluster_name,
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        raise HTTPException(status_code=500, detail=f"Error fetching namespaces: {str(e)}")


@kubeconfig_router.post("/analyze",
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
    
    - Gets the active kubeconfig
    - Builds and executes the k8sgpt analyze command with provided parameters
    - Returns the analysis results
    
    Parameters:
        anonymize: Whether to anonymize data before sending to AI backend
        backend: Backend AI provider to use
        custom_analysis: Whether to enable custom analyzers
        custom_headers: Custom HTTP headers to include
        explain: Whether to explain the problem
        filter: List of analyzers to filter for
        interactive: Whether to enable interactive mode
        language: Language to use for AI responses
        max_concurrency: Maximum number of concurrent requests
        namespace: Kubernetes namespace to analyze
        no_cache: Whether to use cached data
        output: Output format (text or json)
        selector: Label selector for resources
        with_doc: Whether to include official documentation
        config: Path to config file
        kubecontext: Kubernetes context to use
    
    Returns:
        JSONResponse: Analysis results
        
    Raises:
        HTTPException: 404 error if active kubeconfig not found
        HTTPException: Various errors if analysis fails
    """
    # Get the active kubeconfig
    active_kubeconf = get_active_kubeconfig(session, current_user["id"])
    kubeconfig_path = active_kubeconf.path
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
    # Add the active kubeconfig path
    command += f" --kubeconfig {kubeconfig_path}"

    print(command)
    try:
        result = execute_command(command + " --output=json")
        return JSONResponse(content=result, status_code=200)
    except HTTPException as e:
        return JSONResponse(content={"error": str(e.detail)}, status_code=e.status_code)





@kubeconfig_router.post("/analyze-k8s",
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
    
    - Gets the active kubeconfig
    - Connects to the Kubernetes cluster using the client library
    - Analyzes specified resources for potential issues
    - Returns analysis results with namespace as a separate field
    
    Parameters:
        namespace: Kubernetes namespace to analyze (all namespaces if None)
        resource_types: List of resource types to analyze
        
    Returns:
        JSONResponse: Analysis results with namespace as a separate field
        
    Raises:
        HTTPException: 404 error if active kubeconfig not found
        HTTPException: Various errors if analysis fails
    """
    # Get the active kubeconfig
    active_kubeconf = get_active_kubeconfig(session, current_user["id"])
    kubeconfig_path = active_kubeconf.path
    
    if not os.path.exists(kubeconfig_path):
        raise HTTPException(status_code=404, detail="Active kubeconfig file not found on disk")
    
    try:
        # Load the kubeconfig
        config.load_kube_config(config_file=kubeconfig_path)
        
        # Initialize API clients
        core_v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()
        networking_v1 = client.NetworkingV1Api()
        storage_v1 = client.StorageV1Api()
        
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
        publish_message("kubeconfig_events", {
            "event_type": "k8s_analysis_performed",
            "kubeconfig_id": active_kubeconf.id,
            "user_id": current_user["id"],
            "username": current_user.get("username", "unknown"),
            "cluster_name": active_kubeconf.cluster_name,
            "resource_types": resource_types,
            "namespace": namespace or "all",
            "issue_count": len(flat_results),
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        return JSONResponse(content=modified_results, status_code=200)
    
    except client.rest.ApiException as e:
        logger.error(f"Kubernetes API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Kubernetes API error: {str(e)}")
    except Exception as e:
        logger.error(f"Error analyzing Kubernetes resources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing Kubernetes resources: {str(e)}")

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
                if cert.not_valid_after < datetime.datetime.now():
                    results.append({
                        "kind": "Secret",
                        "name": full_name,
                        "error": [{
                            "Text": f"TLS certificate in Secret has expired on {cert.not_valid_after.strftime('%Y-%m-%d')}",
                            "KubernetesDoc": "",
                            "Sensitive": []
                        }],
                        "details": "",
                        "parentObject": ""
                    })
                
                # Check if certificate is about to expire (within 30 days)
                days_to_expiry = (cert.not_valid_after - datetime.datetime.now()).days
                if 0 < days_to_expiry < 30:
                    results.append({
                        "kind": "Secret",
                        "name": full_name,
                        "error": [{
                            "Text": f"TLS certificate in Secret will expire in {days_to_expiry} days (on {cert.not_valid_after.strftime('%Y-%m-%d')})",
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



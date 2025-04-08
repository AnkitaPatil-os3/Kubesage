from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session, select, update
from typing import List, Dict, Optional
import os, uuid, json, subprocess, shlex, datetime  # Added datetime
 
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
 
@kubeconfig_router.post("/upload", response_model=KubeconfigResponse, status_code=201)
async def upload_kubeconfig(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    logger.info(f"Upload request received for user {current_user['id']} with file {file.filename}")
    try:
        # Generate a unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        
        # Get cluster name
        command = f"kubectl config view --kubeconfig {file_path} --minify -o jsonpath='{{.clusters[0].name}}'"
        result = execute_command(command)
        cluster_name = result.get("stdout", "").strip()
        
        # Get context name
        command = f"kubectl config view --kubeconfig {file_path} --minify -o jsonpath='{{.contexts[0].name}}'"
        result = execute_command(command)
        context_name = result.get("stdout", "").strip()
        
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
    except Exception as e:
            logger.error(f"Error uploading kubeconfig: {str(e)}")
            raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
 
@kubeconfig_router.put("/activate/{filename}")
async def set_active_kubeconfig(
        filename: str,
        session: Session = Depends(get_session),
        current_user: Dict = Depends(get_current_user)
):
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
 
@kubeconfig_router.get("/list", response_model=KubeconfigList)
async def list_kubeconfigs(
        session: Session = Depends(get_session),
        current_user: Dict = Depends(get_current_user)
):
        kubeconfigs = session.exec(
            select(Kubeconf)
            .where(Kubeconf.user_id == current_user["id"])
            .order_by(Kubeconf.created_at.desc())
        ).all()
    
        return {"kubeconfigs": kubeconfigs}
 
@kubeconfig_router.get("/clusters", response_model=ClusterNamesResponse)
async def get_cluster_names(
        session: Session = Depends(get_session),
        current_user: Dict = Depends(get_current_user)
):
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
 
@kubeconfig_router.delete("/remove")
async def remove_kubeconfig(
        filename: str = Query(..., description="Filename of the kubeconfig to remove"),
        session: Session = Depends(get_session),
        current_user: Dict = Depends(get_current_user)
):
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
 
@kubeconfig_router.post("/install-operator")
async def install_operator(
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
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
 
@kubeconfig_router.get("/namespaces")
async def get_namespaces(
            session: Session = Depends(get_session),
            current_user: Dict = Depends(get_current_user)
):
            active_kubeconf = get_active_kubeconfig(session, current_user["id"])
            kubeconfig_path = active_kubeconf.path
 
            if not os.path.exists(kubeconfig_path):
                raise HTTPException(status_code=404, detail="Active kubeconfig file not found on disk")
 
            command = f"kubectl get namespaces -o jsonpath='{{.items[*].metadata.name}}' --kubeconfig {kubeconfig_path}"
 
            try:
                result = execute_command(command)
        
                # Check if result is a dictionary with 'stdout' key
                if isinstance(result, dict) and 'stdout' in result:
                    namespaces = result['stdout'].strip().split()
                else:
                    # If result is not in the expected format, raise an exception
                    raise ValueError("Unexpected result format from execute_command")
 
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
            except HTTPException as he:
                # Re-raise HTTP exceptions
                raise he
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
 
 
@kubeconfig_router.post("/analyze")
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
 
    try:

        result = execute_command(command + " --output=json")

        return JSONResponse(content=result, status_code=200)

    except HTTPException as e:

        return JSONResponse(content={"error": str(e.detail)}, status_code=e.status_code)
 
 
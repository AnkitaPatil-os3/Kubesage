from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import subprocess
import shlex

from app.database import get_session
from app.models import AIBackend, AnalysisResult
from app.services import (
    run_k8sgpt_analysis,
    get_analysis_result,
    list_analysis_results,
    add_ai_backend,
    list_ai_backends,
    get_ai_backend,
    delete_ai_backend,
    set_default_ai_backend,
    get_available_analyzers,
    execute_k8sgpt_command,
    save_analysis_result
)
from app.schemas import (
    AnalysisRequest,
    AnalysisResultResponse,
    AnalysisResultsList,
    AIBackendConfigRequest,
    AIBackendConfigResponse,
    AIBackendsList,
    MessageResponse
)
from app.auth import get_current_user
from app.cache import cache_get, cache_set
from app.queue import (
    publish_analysis_started,
    publish_analysis_completed,
    publish_analysis_failed,
    publish_backend_added,
    publish_backend_updated,
    publish_backend_deleted
)
from app.logger import logger

k8sgpt_router = APIRouter()
@k8sgpt_router.post("/analyze", response_model=AnalysisResultResponse)
async def analyze_cluster(
    analysis_request: AnalysisRequest,
    session: Session = Depends(get_session),
    # current_user: Dict = Depends(get_current_user)
):
    """
    Run K8sGPT analysis on the active Kubernetes cluster
    """
    # user_id = current_user["id"]
    user_id = "1"
    analysis_id = str(uuid.uuid4())
    
    # Convert analysis_request to dict for parameter passing
    parameters = analysis_request.dict()
    
    # Publish analysis started event
    analysis_data = {
        "analysis_id": analysis_id,
        "user_id": user_id,
        "namespace": parameters.get("namespace"),
        "timestamp": datetime.utcnow().isoformat()
    }
    publish_analysis_started(analysis_data)
    
    try:
        # Run analysis
        analysis_result = await run_k8sgpt_analysis(
            user_id=user_id,
            parameters=parameters,
            session=session
        )
        
        # Parse the result for the response
        result_json = json.loads(analysis_result.result_json)
        parameters_json = json.loads(analysis_result.parameters)
        
        # Extract the items from the result
        items = []
        if isinstance(result_json, list):
            for item in result_json:
                items.append({
                    "name": item.get("name", ""),
                    "kind": item.get("kind", ""),
                    "namespace": item.get("namespace", ""),
                    "status": item.get("status", ""),
                    "severity": item.get("severity", ""),
                    "message": item.get("message", ""),
                    "hint": item.get("hint", None),
                    "explanation": item.get("explanation", None),
                    "docs": item.get("docs", None)
                })
        
        # Publish analysis completed event
        analysis_data["result_id"] = analysis_result.result_id
        analysis_data["summary"] = items
        publish_analysis_completed(analysis_data)
        
        return {
            "result_id": analysis_result.result_id,
            "cluster_name": analysis_result.cluster_name,
            "namespace": analysis_result.namespace,
            "items": items,
            "created_at": analysis_result.created_at,
            "parameters": parameters_json
        }
    except Exception as e:
        # Publish analysis failed event
        analysis_data["error"] = str(e)
        publish_analysis_failed(analysis_data)
        raise HTTPException(status_code=500, detail=str(e))


@k8sgpt_router.get("/analysis/{result_id}", response_model=AnalysisResultResponse)
async def get_analysis(
    result_id: str,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get a specific analysis result
    """
    user_id = current_user["id"]
    
    analysis_data = await get_analysis_result(
        user_id=user_id,
        result_id=result_id,
        session=session
    )
    
    # Extract the items from the result
    items = []
    result_json = analysis_data["result"]
    if isinstance(result_json, list):
        for item in result_json:
            items.append({
                "name": item.get("name", ""),
                "kind": item.get("kind", ""),
                "namespace": item.get("namespace", ""),
                "status": item.get("status", ""),
                "severity": item.get("severity", ""),
                "message": item.get("message", ""),
                "hint": item.get("hint", None),
                "explanation": item.get("explanation", None),
                "docs": item.get("docs", None)
            })
    
    return {
        "result_id": analysis_data["result_id"],
        "cluster_name": analysis_data["cluster_name"],
        "namespace": analysis_data["namespace"],
        "items": items,
        "created_at": analysis_data["created_at"],
        "parameters": analysis_data["parameters"]
    }

@k8sgpt_router.get("/analyses", response_model=AnalysisResultsList)
async def list_analyses(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    List analysis results for the user
    """
    user_id = current_user["id"]
    
    results = await list_analysis_results(
        user_id=user_id,
        session=session,
        limit=limit,
        offset=offset
    )
    
    # Transform results for the response
    transformed_results = []
    for result in results:
        # Get detailed result
        detailed_result = await get_analysis_result(
            user_id=user_id,
            result_id=result["result_id"],
            session=session
        )
        
        # Extract items
        items = []
        result_json = detailed_result["result"]
        if isinstance(result_json, list):
            for item in result_json:
                items.append({
                    "name": item.get("name", ""),
                    "kind": item.get("kind", ""),
                    "namespace": item.get("namespace", ""),
                    "status": item.get("status", ""),
                    "severity": item.get("severity", ""),
                    "message": item.get("message", ""),
                    "hint": item.get("hint", None),
                    "explanation": item.get("explanation", None),
                    "docs": item.get("docs", None)
                })
        
        transformed_results.append({
            "result_id": detailed_result["result_id"],
            "cluster_name": detailed_result["cluster_name"],
            "namespace": detailed_result["namespace"],
            "items": items,
            "created_at": detailed_result["created_at"],
            "parameters": detailed_result["parameters"]
        })
    
    return {"results": transformed_results}

@k8sgpt_router.post("/backends", response_model=AIBackendConfigResponse)
async def create_backend(
    backend_config: AIBackendConfigRequest,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Add or update an AI backend configuration
    """
    user_id = current_user["id"]
    print("Received backend config:", backend_config)

    # Construct command similar to /auth/add
    command = f"k8sgpt auth add --backend {backend_config.backend_type}"

    if backend_config.baseurl:
        command += f" --baseurl {backend_config.baseurl}"
    if backend_config.maxtokens:
        command += f" --maxtokens {backend_config.maxtokens}"
    if backend_config.model:
        command += f" --model {backend_config.model}"
    if backend_config.temperature:
        command += f" --temperature {backend_config.temperature}"

    # Execute command and handle response
    try:
        output = execute_command(command)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Create a new backend config entry in the database
    db_backend = AIBackend(
        user_id=user_id,
        backend_type=backend_config.backend_type,
        is_default=backend_config.is_default,
        name=backend_config.backend_type,
        api_key=backend_config.api_key,
        organization_id=backend_config.organizationId,
        model=backend_config.model,
        base_url=backend_config.baseurl,
        engine=backend_config.engine,
        temperature=backend_config.temperature,
        max_tokens=backend_config.maxtokens
    )

    # Add and commit the new backend config to the database
    session.add(db_backend)
    session.commit()
    session.refresh(db_backend)  # Get the latest DB values (like id, created_at, etc.)

    # Return the saved backend config response
    return AIBackendConfigResponse(
        id=db_backend.id,
        backend_name=db_backend.backend_type,
        model=db_backend.model,  # Ensure this field exists in the database model
        is_default=db_backend.is_default
    )



@k8sgpt_router.get("/backends/", response_model=AIBackendsList)
async def get_backends(
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    List AI backend configurations for the user
    """
    user_id = current_user["id"]
    backends = await list_ai_backends(user_id=user_id)
 
    return {"backends": backends}


@k8sgpt_router.get("/backends/{backend_name}", response_model=AIBackendConfigResponse)
async def get_backend(
    backend_name: str,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get a specific AI backend configuration
    """
    user_id = current_user["id"]
    
    backend = await get_ai_backend(
        user_id=user_id,
        backend_name=backend_name,
        session=session
    )
    
    return backend


@k8sgpt_router.delete("/backends/{backend_name}", response_model=MessageResponse)
async def remove_backend(
    backend_name: str,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Delete an AI backend configuration from both the database and the terminal
    """
    user_id = current_user["id"]
    # Query the database for the backend configuration
    backend = session.query(AIBackend).filter_by(user_id=user_id, backend_type=backend_name).first()
    if not backend:
        raise HTTPException(status_code=404, detail=f"Backend {backend_name} not found for user {user_id}")
    # Construct the terminal command
    command = f"k8sgpt auth remove -b {backend_name}"
    # Execute the command to remove from terminal
    try:
        output = execute_command(command)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove backend from terminal: {str(e)}")
    # Delete the backend from the database
    session.delete(backend)
    session.commit()
    return {"message": f"Backend {backend_name} deleted successfully from database and terminal"}


@k8sgpt_router.put("/backends/{backend_name}/default", response_model=MessageResponse)
async def set_default_backend(
    backend_name: str,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Set a backend as the default in both the database and terminal
    """
    user_id = current_user["id"]

    # Query the database for the backend configuration
    backend = session.query(AIBackend).filter_by(user_id=user_id, backend_type=backend_name).first()
    
    if not backend:
        raise HTTPException(status_code=404, detail=f"Backend {backend_name} not found for user {user_id}")

    # Update all backends for the user to is_default=False
    session.query(AIBackend).filter_by(user_id=user_id).update({"is_default": False})
    
    # Set the selected backend as default
    backend.is_default = True
    session.commit()

    # Construct the terminal command
    command = f"k8sgpt auth default {backend_name}"

    # Execute the command to set default in terminal
    try:
        output = execute_command(command)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set default backend in terminal: {str(e)}")

    return {"message": f"Backend {backend_name} set as default successfully in database and terminal"}


@k8sgpt_router.get("/analyzers", response_model=List[str])
async def list_analyzers(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get available K8sGPT analyzers
    """
    user_id = current_user["id"]
    
    analyzers = await get_available_analyzers(user_id)
    
    return analyzers


def execute_command(command: str):
    print(command)
    try:
        args = shlex.split(command)
        result = subprocess.run(args, check=True, capture_output=True, text=True)
        # Try to parse the output as JSON
        try:
            output = json.loads(result.stdout)
            return output
        except json.JSONDecodeError:
            # If parsing fails, return the raw output
            return {"stdout": result.stdout}
 
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Command execution failed: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
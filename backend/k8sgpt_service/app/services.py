import json
import os
import uuid
import subprocess
import shlex
from typing import Dict, List, Any, Optional
from sqlmodel import Session, select
from app.models import AIBackend, AnalysisResult
from app.logger import logger
from app.config import settings
from app.cache import cache_delete, cache_flush_user

def delete_user_data(user_id: int):
    """Delete all data belonging to a specific user when they are deleted"""
    from sqlmodel import Session
    from app.database import engine
    
    try:
        with Session(engine) as session:
            # Delete AI backends
            delete_user_ai_backends(user_id, session)
            
            # Delete analysis results
            delete_user_analysis_results(user_id, session)
            
            # Clear user cache
            cache_flush_user(user_id)
            
            logger.info(f"Deleted all data for user {user_id}")
    except Exception as e:
        logger.error(f"Error deleting data for user {user_id}: {str(e)}")

def delete_user_ai_backends(user_id: int, session: Session):
    """Delete all AI backends belonging to a user"""
    from app.models import AIBackend
    
    # Find all AI backends for this user
    backends = session.exec(
        select(AIBackend).where(AIBackend.user_id == user_id)
    ).all()
    
    # Delete each backend
    for backend in backends:
        session.delete(backend)
    
    # Commit the changes
    session.commit()
    logger.info(f"Deleted all AI backends for user {user_id}")

def delete_user_analysis_results(user_id: int, session: Session):
    """Delete all analysis results belonging to a user"""
    from app.models import AnalysisResult
    import os
    
    # Find all analysis results for this user
    results = session.exec(
        select(AnalysisResult).where(AnalysisResult.user_id == user_id)
    ).all()
    
    # Delete each result and its associated file
    for result in results:
            # Delete the result file if it exists
            file_path = result.file_path
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted analysis result file: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting analysis result file {file_path}: {str(e)}")
        
            # Delete the database entry
            session.delete(result)
    
            # Commit all deletions
            session.commit()
            logger.info(f"Deleted all analysis results for user {user_id}")

def execute_k8sgpt_command(command: str) -> Dict[str, Any]:
        """Execute a K8sGPT CLI command and return the result"""
        logger.info(f"Executing command: {command}")
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
            logger.error(f"Command execution failed: {e.stderr}")
            return {"error": e.stderr}
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return {"error": str(e)}

def save_analysis_result(user_id: int, result: Dict[str, Any], namespace: Optional[str] = None) -> AnalysisResult:
        """Save analysis result to database and file system"""
        from app.database import engine
    
        # Generate unique filename
        filename = f"analysis_{user_id}_{uuid.uuid4()}.json"
        file_path = os.path.join(settings.ANALYSIS_DIR, filename)
    
        # Save result to file
        with open(file_path, 'w') as f:
            json.dump(result, f, indent=2)
    
        # Create analysis result object
        analysis_result = AnalysisResult(
            user_id=user_id,
            file_path=file_path,
            namespace=namespace,
            summary=extract_summary(result)
        )
    
        # Save to database
        with Session(engine) as session:
            session.add(analysis_result)
            session.commit()
            session.refresh(analysis_result)
    
        return analysis_result

def extract_summary(result: Dict[str, Any]) -> str:
        """Extract a summary from analysis result"""
        try:
            # This will depend on the format of your K8sGPT output
            if "results" in result and isinstance(result["results"], list):
                issues = len(result["results"])
                return f"Found {issues} potential issues in the cluster"
            return "Analysis completed"
        except Exception as e:
            logger.error(f"Error extracting summary: {str(e)}")
            return "Analysis completed"

def run_k8sgpt_analysis(
    user_id: int,
    kubeconfig_path: str,
    namespace: Optional[str] = None,
    filters: Optional[List[str]] = None,
    anonymize: bool = False,
    explain: bool = True,
    language: str = "english",
    output_format: str = "json",
    no_cache: bool = False,
    
    with_doc: bool = False
) -> Dict[str, Any]:
    """
    Run a K8sGPT analysis using the specified parameters
    
    Args:
        user_id: ID of the user running the analysis
        kubeconfig_path: Path to the kubeconfig file
        namespace: Optional namespace to analyze
        filters: Optional list of analyzers to filter
        anonymize: Whether to anonymize data
        explain: Whether to explain the problem
        language: Language to use for AI
        output_format: Output format (text, json)
        no_cache: Whether to use cached data
        with_doc: Whether to include documentation
        
    Returns:
        Dictionary containing the analysis results
    """
    
    # Construct the command
    command = "k8sgpt analyze"
    
    if anonymize:
        command += " --anonymize"
    if explain:
        command += " --explain"
    if filters:
        for f in filters:
            command += f" --filter {f}"
    if language and language != "english":
        command += f" --language {language}"
    if namespace:
        command += f" --namespace {namespace}"
    if no_cache:
        command += " --no-cache"
    if output_format:
        command += f" --output {output_format}"
    if with_doc:
        command += " --with-doc"
    
    # Add the kubeconfig path
    command += f" --kubeconfig {kubeconfig_path}"
    
    # Execute the command
    analysis_result = execute_k8sgpt_command(command)
    
    # Save the analysis result if it was successful
    if "error" not in analysis_result:
        saved_result = save_analysis_result(user_id, analysis_result, namespace)
        analysis_result["result_id"] = saved_result.id
    
    return analysis_result

def get_analysis_result(result_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve an analysis result by ID
    
    Args:
        result_id: ID of the analysis result to retrieve
        user_id: Optional user ID for permission check
        
    Returns:
        Dictionary containing the analysis result data or None if not found
    """
    from app.database import engine
    from sqlmodel import Session, select
    
    with Session(engine) as session:
        query = select(AnalysisResult).where(AnalysisResult.id == result_id)
        
        # If user_id is provided, add it to the query to ensure the user owns this result
        if user_id is not None:
            query = query.where(AnalysisResult.user_id == user_id)
            
        result = session.exec(query).first()
        
        if not result:
            return None
            
        # Load the result data from file
        try:
            with open(result.file_path, 'r') as f:
                analysis_data = json.load(f)
                
            # Combine database metadata with file content
            return {
                "id": result.id,
                "user_id": result.user_id,
                "namespace": result.namespace,
                "summary": result.summary,
                "created_at": result.created_at.isoformat(),
                "analysis": analysis_data
            }
        except Exception as e:
            logger.error(f"Error reading analysis result file {result.file_path}: {str(e)}")
            return {
                "id": result.id,
                "user_id": result.user_id,
                "namespace": result.namespace,
                "summary": result.summary,
                "created_at": result.created_at.isoformat(),
                "error": "Failed to load analysis data file"
            }

def list_analysis_results(
    user_id: int,
    namespace: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "created_at",
    sort_desc: bool = True
) -> List[Dict[str, Any]]:
    """
    List analysis results for a specific user with optional filtering
    
    Args:
        user_id: ID of the user whose results to retrieve
        namespace: Optional namespace to filter results
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        sort_by: Field to sort by
        sort_desc: Whether to sort in descending order
        
    Returns:
        List of dictionaries containing analysis result metadata
    """
    from app.database import engine
    from sqlmodel import Session, select, col
    
    with Session(engine) as session:
        query = select(AnalysisResult).where(AnalysisResult.user_id == user_id)
        
        # Apply namespace filter if provided
        if namespace:
            query = query.where(AnalysisResult.namespace == namespace)
        
        # Apply sorting
        if hasattr(AnalysisResult, sort_by):
            sort_col = getattr(AnalysisResult, sort_by)
            if sort_desc:
                query = query.order_by(sort_col.desc())
            else:
                query = query.order_by(sort_col)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        results = session.exec(query).all()
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "namespace": result.namespace,
                "summary": result.summary,
                "created_at": result.created_at.isoformat()
            })
        
        return formatted_results
    
def add_ai_backend(
    user_id: int,
    backend_type: str,
    name: str,
    api_key: str,
    engine: str,
    model: str = "gpt-3.5-turbo",
    organization_id: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    set_as_default: bool = False
) -> AIBackend:

    """
    Add a new AI backend for a user
    
    Args:
        user_id: ID of the user
        backend_type: Type of AI backend (openai, azureopenai, etc.)
        name: Name of the backend
        api_key: API key for the backend
        model: Model to use
        organization_id: Optional organization ID
        base_url: Optional base URL for the API
        engine: Optional engine name (for Azure)
        temperature: Temperature for generation
        max_tokens: Maximum tokens for generation
        set_as_default: Whether to set this as the default backend
        
    Returns:
        The created AIBackend instance
    """
    from app.database import engine
    from sqlmodel import Session, select
    from app.queue import publish_backend_added
    
    with Session(engine) as session:
        # If set_as_default is True, unset any existing default backends
        if set_as_default:
            existing_defaults = session.exec(
                select(AIBackend).where(
                    AIBackend.user_id == user_id,
                    AIBackend.is_default == True
                )
            ).all()
            
            for default_backend in existing_defaults:
                default_backend.is_default = False
                session.add(default_backend)
        
        # Create new backend
        new_backend = AIBackend(
            user_id=user_id,
            backend_type=backend_type,
            name=name,
            api_key=api_key,
            model=model,
            organization_id=organization_id,
            base_url=base_url,
            engine=engine,
            temperature=temperature,
            max_tokens=max_tokens,
            is_default=set_as_default
        )
        
        session.add(new_backend)
        session.commit()
        session.refresh(new_backend)
        
        # Publish event to message queue
        backend_data = {
            "id": new_backend.id,
            "user_id": new_backend.user_id,
            "backend_type": new_backend.backend_type,
            "name": new_backend.name,
            "model": new_backend.model,
            "is_default": new_backend.is_default
        }
        publish_backend_added(backend_data)
        

        return new_backend

async def list_ai_backends(
    user_id: int,
    backend_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    List AI backends for a specific user with optional filtering
    Args:
        user_id: ID of the user whose backends to retrieve
        backend_type: Optional backend type to filter by
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
    Returns:
        List of dictionaries containing AI backend data
    """
    from app.database import engine
    from sqlmodel import Session, select
    with Session(engine) as session:
        query = select(AIBackend).where(AIBackend.user_id == user_id)
        # Apply backend type filter if provided
        if backend_type:
            query = query.where(AIBackend.backend_type == backend_type)
        # Apply pagination
        query = query.offset(skip).limit(limit)
        # Execute query
        backends = session.exec(query).all()
        # Format results (hiding sensitive information like API keys)
        formatted_backends = []
        for backend in backends:
            formatted_backends.append({
                "id": backend.id,
                "backend_name": backend.name,
                "backend_type": backend.backend_type,
                "model": backend.model,
                "is_default": backend.is_default,
                # "organization_id": backend.organization_id,
                "base_url": backend.base_url,
                # "engine": backend.engine,
                "temperature": backend.temperature,
                "max_tokens": backend.max_tokens,
                "created_at": backend.created_at.isoformat(),
                "updated_at": backend.updated_at.isoformat()
            })
        print("Hii", formatted_backends)
        return formatted_backends
 
def get_ai_backend(backend_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Get a specific AI backend by ID
    
    Args:
        backend_id: ID of the backend to retrieve
        user_id: Optional user ID for permission check
        
    Returns:
        Dictionary containing the backend data or None if not found
    """
    from app.database import engine
    from sqlmodel import Session, select
    
    with Session(engine) as session:
        query = select(AIBackend).where(AIBackend.id == backend_id)
        
        # If user_id is provided, add it to the query to ensure the user owns this backend
        if user_id is not None:
            query = query.where(AIBackend.user_id == user_id)
            
        backend = session.exec(query).first()
        
        if not backend:
            return None
            
        # Return backend data (excluding sensitive information like API key)
        return {
            "id": backend.id,
            "user_id": backend.user_id,
            "name": backend.name,
            "backend_type": backend.backend_type,
            "model": backend.model,
            "is_default": backend.is_default,
            "organization_id": backend.organization_id,
            "base_url": backend.base_url,
            "engine": backend.engine,
            "temperature": backend.temperature,
            "max_tokens": backend.max_tokens,
            "created_at": backend.created_at.isoformat(),
            "updated_at": backend.updated_at.isoformat()
        }

def delete_ai_backend(backend_id: int, user_id: int) -> bool:
    """
    Delete an AI backend by ID
    
    Args:
        backend_id: ID of the backend to delete
        user_id: User ID for permission check
        
    Returns:
        True if successfully deleted, False otherwise
    """
    from app.database import engine
    from sqlmodel import Session, select
    from app.queue import publish_backend_deleted
    
    with Session(engine) as session:
        # Find the backend with user_id check for permission
        query = select(AIBackend).where(
            AIBackend.id == backend_id,
            AIBackend.user_id == user_id
        )
        backend = session.exec(query).first()
        
        if not backend:
            return False
            
        # Store backend info for event publishing
        backend_data = {
            "id": backend.id,
            "user_id": backend.user_id,
            "name": backend.name,
            "backend_type": backend.backend_type
        }
        
        # Delete the backend
        session.delete(backend)
        session.commit()
        
        # Publish event to message queue
        publish_backend_deleted(backend_data)
        
        return True

def set_default_ai_backend(backend_id: int, user_id: int) -> bool:
    """
    Set an AI backend as the default for a user
    
    Args:
        backend_id: ID of the backend to set as default
        user_id: User ID for permission check
        
    Returns:
        True if successfully set as default, False otherwise
    """
    from app.database import engine
    from sqlmodel import Session, select
    from app.queue import publish_backend_updated
    
    with Session(engine) as session:
        # Find the backend with user_id check for permission
        query = select(AIBackend).where(
            AIBackend.id == backend_id,
            AIBackend.user_id == user_id
        )
        backend = session.exec(query).first()
        
        if not backend:
            return False
        
        # Unset any existing default backends for this user
        existing_defaults = session.exec(
            select(AIBackend).where(
                AIBackend.user_id == user_id,
                AIBackend.is_default == True,
                AIBackend.id != backend_id  # Don't include the one we're setting
            )
        ).all()
        
        for default_backend in existing_defaults:
            default_backend.is_default = False
            session.add(default_backend)
        
        # Set the selected backend as default
        backend.is_default = True
        session.add(backend)
        session.commit()
        
        # Publish event to message queue
        backend_data = {
            "id": backend.id,
            "user_id": backend.user_id,
            "name": backend.name,
            "backend_type": backend.backend_type,
            "is_default": True
        }
        publish_backend_updated(backend_data)
        
        return True

def get_available_analyzers(kubeconfig_path: Optional[str] = None) -> List[str]:
    """
    Get a list of available analyzers from k8sgpt
    
    Args:
        kubeconfig_path: Optional path to a kubeconfig file
        
    Returns:
        List of available analyzer names
    """
    # Construct the command to list filters
    command = "k8sgpt filters list"
    
    # Add kubeconfig path if provided
    if kubeconfig_path:
        command += f" --kubeconfig {kubeconfig_path}"
    
    # Execute the command
    result = execute_k8sgpt_command(command)
    
    # Parse the result
    analyzers = []
    
    if isinstance(result, dict):
        # Handle different output formats
        if "stdout" in result:
            # Line-by-line output format
            analyzers = [
                line.strip() 
                for line in result["stdout"].split("\n") 
                if line.strip()
            ]
        elif isinstance(result, list):
            # JSON list format
            analyzers = result
        
    logger.info(f"Found {len(analyzers)} available analyzers")
    return analyzers

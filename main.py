from fastapi import FastAPI, HTTPException, status, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from pydantic import BaseModel
from typing import List, Optional
import logging     
from models import K8sGPTCRD, ResultCRD
from services import K8sGPTCRDService, ResultCRDService
import json

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="K8sGPT CRD API",
    description="API for managing K8sGPT Custom Resource Definitions",
    version="0.1.0",
    openapi_tags=[{
        "name": "k8sgpt",
        "description": "Operations with K8sGPT CRDs"
    }, {
        "name": "results",
        "description": "Operations with Result CRDs"
    }]
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load kubeconfig
try:
    config.load_kube_config()
    logger.info("Loaded kubeconfig successfully")
except config.ConfigException:
    logger.warning("Failed to load kubeconfig, trying in-cluster config")
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster config successfully")
    except config.ConfigException as e:
        logger.error("Failed to load any Kubernetes configuration")
        raise RuntimeError("Failed to initialize Kubernetes client") from e

# Error handlers
@app.exception_handler(ApiException)
async def kubernetes_api_exception_handler(request, exc):
    logger.error(f"Kubernetes API error: {exc}")
    raise HTTPException(
        status_code=exc.status,
        detail={
            "kind": "Status",
            "apiVersion": "v1",
            "metadata": {},
            "status": "Failure",
            "message": exc.body if hasattr(exc, 'body') else str(exc),
            "reason": "BadRequest",
            "code": exc.status
        }
    )

# K8sGPT CRD Endpoints
@app.post("/k8sgpt/{namespace}", tags=["k8sgpt"], status_code=status.HTTP_201_CREATED)
async def create_k8sgpt(namespace: str, k8sgpt: K8sGPTCRD):
    # Convert to dict and ensure proper structure
    crd_data = k8sgpt.dict(by_alias=True)
    
    # Set default metadata if missing
    if not crd_data.get("metadata"):
        crd_data["metadata"] = {}
    
    # Set default name if missing
    if not crd_data["metadata"].get("name"):
        crd_data["metadata"]["name"] = f"k8sgpt-{namespace}"
    
    # Log the final payload
    logger.info(f"Final CRD payload: {crd_data}")
    
    # Create the CRD
    try:
        return K8sGPTCRDService.create_k8sgpt(
            namespace,
            K8sGPTCRD(**crd_data)
        )
    except ApiException as e:
        logger.error(f"Kubernetes API error: {e}")
        raise HTTPException(
            status_code=e.status,
            detail=e.body if hasattr(e, 'body') else str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "kind": "Status",
                "apiVersion": "v1",
                "metadata": {},
                "status": "Failure",
                "message": "metadata.name is required",
                "reason": "Invalid",
                "details": {
                    "group": "core.k8sgpt.ai",
                    "kind": "K8sGPT",
                    "causes": [{
                        "reason": "FieldValueRequired",
                        "message": "Required value: name is required",
                        "field": "metadata.name"
                    }]
                },
                "code": 422
            }
        )
    return K8sGPTCRDService.create_k8sgpt(namespace, k8sgpt)

@app.get("/k8sgpt/{namespace}/{name}", tags=["k8sgpt"])
async def get_k8sgpt(
    namespace: str = Path(..., description="Namespace of the K8sGPT resource"),
    name: str = Path(..., description="Name of the K8sGPT resource")
):
    return K8sGPTCRDService.get_k8sgpt(namespace, name)

@app.get("/k8sgpt", tags=["k8sgpt"])
async def list_k8sgpts(
    namespace: Optional[str] = Query(None, description="Filter by namespace")
):
    return K8sGPTCRDService.list_k8sgpts(namespace)

@app.put("/k8sgpt/{namespace}/{name}", tags=["k8sgpt"])
async def update_k8sgpt(
    namespace: str,
    name: str,
    k8sgpt: K8sGPTCRD
):
    return K8sGPTCRDService.update_k8sgpt(namespace, name, k8sgpt)

@app.delete("/k8sgpt/{namespace}/{name}", tags=["k8sgpt"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_k8sgpt(namespace: str, name: str):
    return K8sGPTCRDService.delete_k8sgpt(namespace, name)

@app.get("/k8sgpt/watch", tags=["k8sgpt"])
async def watch_k8sgpts(
    namespace: Optional[str] = Query(None, description="Filter by namespace"),
    timeout: int = Query(60, description="Watch timeout in seconds")
):
    def generate():
        for event in K8sGPTCRDService.watch_k8sgpts(namespace, timeout):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")

# Result CRD Endpoints
@app.post("/results/{namespace}", tags=["results"], status_code=status.HTTP_201_CREATED)
async def create_result(namespace: str, result: ResultCRD):
    return ResultCRDService.create_result(namespace, result)

@app.get("/results/{namespace}/{name}", tags=["results"])
async def get_result(
    namespace: str = Path(..., description="Namespace of the Result resource"),
    name: str = Path(..., description="Name of the Result resource")
):
    return ResultCRDService.get_result(namespace, name)

@app.get("/results", tags=["results"])
async def list_results(
    namespace: Optional[str] = Query(None, description="Filter by namespace")
):
    return ResultCRDService.list_results(namespace)

@app.put("/results/{namespace}/{name}", tags=["results"])
async def update_result(
    namespace: str,
    name: str,
    result: ResultCRD
):
    return ResultCRDService.update_result(namespace, name, result)

@app.delete("/results/{namespace}/{name}", tags=["results"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_result(namespace: str, name: str):
    return ResultCRDService.delete_result(namespace, name)

@app.get("/results/watch", tags=["results"])
async def watch_results(
    namespace: Optional[str] = Query(None, description="Filter by namespace"),
    timeout: int = Query(60, description="Watch timeout in seconds")
):
    def generate():
        for event in ResultCRDService.watch_results(namespace, timeout):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
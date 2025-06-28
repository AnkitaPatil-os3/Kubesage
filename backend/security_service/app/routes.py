from fastapi import APIRouter, HTTPException, Query, Path, Depends
from fastapi.responses import JSONResponse
from typing import Optional
from app.schema import APIResponse, VulnerabilityFilter
from app.service import security_service
from app.auth import get_current_user
from app.logger import logger
from datetime import datetime

# Create router
router = APIRouter()

@router.get("/", response_model=dict)
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Kubernetes Security Service API",
        "version": "1.0.0",
        "service": "security-service",
        "endpoints": {
            "/reports": "Get all vulnerability reports",
            "/reports/{namespace}": "Get reports for specific namespace",
            "/reports/summary": "Get vulnerability summary",
            "/reports/summary/{namespace}": "Get summary for specific namespace",
            "/vulnerabilities": "Get all vulnerabilities with filtering options",
            "/vulnerabilities/{namespace}": "Get vulnerabilities for specific namespace",
            "/vulnerabilities/severity/{severity}": "Get vulnerabilities by severity",
            "/vulnerabilities/fixable": "Get fixable vulnerabilities",
            "/namespaces": "Get namespaces with vulnerability reports",
            "/metrics": "Get security metrics overview",
            "/health": "Health check endpoint"
        }
    }

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        return security_service.health_check()
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise

@router.get("/reports", response_model=APIResponse)
async def get_all_reports(current_user: dict = Depends(get_current_user)):
    """Get all vulnerability reports from all namespaces"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} requested all vulnerability reports")
        return security_service.get_all_reports()
    except Exception as e:
        logger.error(f"Error in get_all_reports: {e}")
        raise

@router.get("/reports/{namespace}", response_model=APIResponse)
async def get_reports_by_namespace(
    namespace: str = Path(..., description="Kubernetes namespace"),
    current_user: dict = Depends(get_current_user)
):
    """Get vulnerability reports for a specific namespace"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} requested reports for namespace: {namespace}")
        return security_service.get_reports_by_namespace(namespace)
    except Exception as e:
        logger.error(f"Error in get_reports_by_namespace: {e}")
        raise

@router.get("/reports/summary", response_model=APIResponse)
async def get_vulnerability_summary(current_user: dict = Depends(get_current_user)):
    """Get summary of all vulnerability reports"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} requested vulnerability summary")
        return security_service.get_vulnerability_summary()
    except Exception as e:
        logger.error(f"Error in get_vulnerability_summary: {e}")
        raise

@router.get("/reports/summary/{namespace}", response_model=APIResponse)
async def get_vulnerability_summary_by_namespace(
    namespace: str = Path(..., description="Kubernetes namespace"),
    current_user: dict = Depends(get_current_user)
):
    """Get vulnerability summary for a specific namespace"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} requested summary for namespace: {namespace}")
        return security_service.get_vulnerability_summary(namespace=namespace)
    except Exception as e:
        logger.error(f"Error in get_vulnerability_summary_by_namespace: {e}")
        raise

@router.get("/vulnerabilities", response_model=APIResponse)
async def get_all_vulnerabilities(
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)"),
    fixable_only: Optional[bool] = Query(False, description="Show only fixable vulnerabilities"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    current_user: dict = Depends(get_current_user)
):
    """Get all vulnerabilities with optional filtering"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} requested vulnerabilities with filters: severity={severity}, fixable_only={fixable_only}, limit={limit}")
        return security_service.get_vulnerabilities(
            severity=severity,
            fixable_only=fixable_only,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error in get_all_vulnerabilities: {e}")
        raise

@router.get("/vulnerabilities/{namespace}", response_model=APIResponse)
async def get_vulnerabilities_by_namespace(
    namespace: str = Path(..., description="Kubernetes namespace"),
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)"),
    fixable_only: Optional[bool] = Query(False, description="Show only fixable vulnerabilities"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    current_user: dict = Depends(get_current_user)
):
    """Get vulnerabilities for a specific namespace with optional filtering"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} requested vulnerabilities for namespace: {namespace}")
        return security_service.get_vulnerabilities(
            severity=severity,
            fixable_only=fixable_only,
            limit=limit,
            namespace=namespace
        )
    except Exception as e:
        logger.error(f"Error in get_vulnerabilities_by_namespace: {e}")
        raise

@router.get("/vulnerabilities/severity/{severity}", response_model=APIResponse)
async def get_vulnerabilities_by_severity(
    severity: str = Path(..., description="Severity level (CRITICAL, HIGH, MEDIUM, LOW)"),
    namespace: Optional[str] = Query(None, description="Filter by namespace"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    current_user: dict = Depends(get_current_user)
):
    """Get vulnerabilities by severity level"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} requested {severity} vulnerabilities")
        return security_service.get_vulnerabilities(
            severity=severity,
            namespace=namespace,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error in get_vulnerabilities_by_severity: {e}")
        raise

@router.get("/vulnerabilities/fixable", response_model=APIResponse)
async def get_fixable_vulnerabilities(
    namespace: Optional[str] = Query(None, description="Filter by namespace"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    current_user: dict = Depends(get_current_user)
):
    """Get all fixable vulnerabilities"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} requested fixable vulnerabilities")
        return security_service.get_vulnerabilities(
            severity=severity,
            fixable_only=True,
            limit=limit,
            namespace=namespace
        )
    except Exception as e:
        logger.error(f"Error in get_fixable_vulnerabilities: {e}")
        raise

@router.get("/namespaces", response_model=APIResponse)
async def get_namespaces_with_reports(current_user: dict = Depends(get_current_user)):
    """Get list of namespaces that have vulnerability reports"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} requested namespaces with reports")
        return security_service.get_namespaces_with_reports()
    except Exception as e:
        logger.error(f"Error in get_namespaces_with_reports: {e}")
        raise

@router.get("/metrics", response_model=APIResponse)
async def get_security_metrics(current_user: dict = Depends(get_current_user)):
    """Get overall security metrics"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} requested security metrics")
        return security_service.get_security_metrics()
    except Exception as e:
        logger.error(f"Error in get_security_metrics: {e}")
        raise

# Additional endpoints for advanced filtering
@router.post("/vulnerabilities/search", response_model=APIResponse)
async def search_vulnerabilities(
    filter_params: VulnerabilityFilter,
    current_user: dict = Depends(get_current_user)
):
    """Advanced vulnerability search with multiple filters"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} performed advanced vulnerability search")
        return security_service.get_vulnerabilities(
            severity=filter_params.severity,
            fixable_only=filter_params.fixable_only,
            limit=filter_params.limit,
            namespace=filter_params.namespace
        )
    except Exception as e:
        logger.error(f"Error in search_vulnerabilities: {e}")
        raise
#!/usr/bin/env python3
"""
Security Service - FastAPI Vulnerability Reports Server
This FastAPI server provides multiple endpoints for retrieving and filtering vulnerability reports 
from Trivy Operator using the Kubernetes Python client.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.routes import  policy_router
from app.database import create_tables
from app.logger import logger
from app.config import settings
import uvicorn
from fastapi.responses import JSONResponse
from datetime import datetime


# Create FastAPI app
app = FastAPI(
    title="Kubernetes Security Service API",
    description="API for Kubernetes security monitoring and policy management",
    version=settings.SERVICE_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# app.include_router(router, prefix="/api/v1")
app.include_router(policy_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        create_tables()  # This will create the new policy_applications table
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Security Service shutting down...")

# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "data": None,
            "timestamp": datetime.now().isoformat()
        }
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Kubernetes Security Service API",
        "version": settings.SERVICE_VERSION,
        "service": settings.SERVICE_NAME,
        "endpoints": {
            "/api/v1/": "Security monitoring endpoints",
            "/api/v1/policies/": "Policy management endpoints",
            "/api/v1/policies/apply": "Apply policies to clusters",
            "/api/v1/policies/applications": "Manage policy applications",
            "/docs": "API documentation",
            "/health": "Health check"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8005,
        reload=settings.DEBUG
    )

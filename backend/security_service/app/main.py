#!/usr/bin/env python3
"""
Security Service - FastAPI Vulnerability Reports Server
This FastAPI server provides multiple endpoints for retrieving and filtering vulnerability reports 
from Trivy Operator using the Kubernetes Python client.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.config import settings
from app.logger import logger
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(
    title="Kubernetes Security Service API",
    description="API for retrieving and filtering vulnerability reports from Trivy Operator",
    version=settings.SERVICE_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1/security")

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    try:
        logger.info(f"{settings.SERVICE_NAME} v{settings.SERVICE_VERSION} starting up...")
        logger.info("Security Service started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Security Service: {e}")
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
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "status": "running",
        "docs": "/docs",
        "api": "/api/v1/security",
        "timestamp": datetime.now().isoformat()
    }

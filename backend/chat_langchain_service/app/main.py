from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime

from app.config import settings
from app.database import create_db_and_tables
from app.routes import router
from app.logger import logger
from app.langchain_service import initialize_kubernetes, KUBERNETES_SERVICE_VERSION

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("🚀 Starting KubeSage Simplified Chat Service...")
    logger.info(f"📋 Service Version: {KUBERNETES_SERVICE_VERSION}")
    logger.info(f"🔧 LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"🎯 Kubeconfig: {settings.get_kubeconfig_path()}")
    
    # Initialize database
    try:
        create_db_and_tables()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
    
    # Initialize Kubernetes
    try:
        k8s_status = initialize_kubernetes()
        if k8s_status["success"]:
            logger.info("✅ Kubernetes client initialized successfully")
            logger.info(f"📊 Cluster: {k8s_status.get('cluster_version', 'Unknown version')}")
        else:
            logger.warning(f"⚠️ Kubernetes initialization warning: {k8s_status.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"❌ Kubernetes initialization failed: {e}")
    
    logger.info("🎉 Service startup completed")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down KubeSage Chat Service...")
    logger.info("👋 Service shutdown completed")

# Create FastAPI app
app = FastAPI(
    title="KubeSage Simplified Chat Service",
    description="AI-powered Kubernetes assistant with error collection and direct LLM processing",
    version=KUBERNETES_SERVICE_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    start_time = datetime.utcnow()
    
    # Log request
    logger.info(f"📥 {request.method} {request.url.path} - {request.client.host if request.client else 'unknown'}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"📤 {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"💥 Unhandled exception in {request.method} {request.url.path}: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "kubesage-simplified-chat",
            "version": KUBERNETES_SERVICE_VERSION
        }
    )

# Include routes
app.include_router(router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "KubeSage Simplified Chat Service",
        "version": KUBERNETES_SERVICE_VERSION,
        "description": "AI-powered Kubernetes assistant with error collection and direct LLM processing",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "chat": "/api/v1/chat",
            "health": "/api/v1/health",
            "info": "/api/v1/info",
            "docs": "/docs" if settings.DEBUG else "disabled"
        },
        "features": [
            "Kubernetes error collection",
            "Direct LLM processing",
            "Conversation history",
            "Session management",
            "Multiple LLM providers"
        ]
    }

# Health check endpoint (also available at root level)
@app.get("/health")
async def root_health():
    """Root level health check."""
    return {
        "status": "healthy",
        "service": "kubesage-simplified-chat",
        "version": KUBERNETES_SERVICE_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    logger.info(f"🚀 Starting server on {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
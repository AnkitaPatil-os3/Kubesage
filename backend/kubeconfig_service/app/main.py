from fastapi import FastAPI
from app.routes import cluster_router
from app.database import create_db_and_tables
from app.consumer import start_consumers
from app.logger import logger
from app.config import settings
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI(title="KubeSage KubeConfig Service")

# Allow frontend requests
origins = [
    "*",  # Frontend running locally
]

# ✅ Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow all origins, or specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    try:
        # Create database tables
        create_db_and_tables()
        
        # Start message consumers
        start_consumers()
        
        logger.info("🚀 KubeConfig service started successfully")
        logger.info(f"🗄️ Database URL: {settings.DATABASE_URL}")
        
    except Exception as e:
        logger.error(f"❌ Error during startup: {str(e)}")
        raise

@app.get("/health")
def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "kubeconfig",
        "cleanup_service": "operational"
    }

@app.get("/health/detailed")
def detailed_health_check():
    """Detailed health check including cleanup service status"""
    try:
        from app.database import engine
        from sqlmodel import Session, select
        from app.models import ClusterConfig
        
        # Basic health info
        health_info = {
            "status": "healthy",
            "service": "kubeconfig_service",
            "timestamp": datetime.utcnow().isoformat(),
            "cleanup_service": "operational"
        }
        
        # Add database connectivity check
        try:
            with Session(engine) as session:
                # Simple query to test database
                session.exec(select(ClusterConfig).limit(1)).first()
            health_info["database"] = "connected"
        except Exception as e:
            health_info["database"] = f"error: {str(e)}"
            health_info["status"] = "degraded"
        
        return health_info
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "kubeconfig_service",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Include routers
app.include_router(cluster_router, prefix="/kubeconfig", tags=["kubeconfig"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8001, 
        reload=getattr(settings, 'DEBUG', False),
        ssl_keyfile=getattr(settings, 'SSL_KEYFILE', "key.pem"), 
        ssl_certfile=getattr(settings, 'SSL_CERTFILE', "cert.pem")
    )

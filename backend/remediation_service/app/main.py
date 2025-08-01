from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import remediation_router
from app.database import create_db_and_tables
from app.logger import logger
from app.config import settings

app = FastAPI(
    title="KubeSage Remediation Service",
    description="AI-powered Kubernetes incident remediation service",
    version="1.0.0"
)

# Configure CORS
origins = [
    "https://localhost:3000",
    "https://10.0.2.30:5173",
    "https://127.0.0.1:3000",
    "*"  # Allow all origins for development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    try:
        # Create database tables
        create_db_and_tables()
        
        logger.info("Remediation service started successfully")
        logger.info(f"LLM enabled: {settings.LLM_ENABLED}")
        logger.info(f"Database URL: {settings.DATABASE_URL}")
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

@app.get("/health")
def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "remediation",
        "llm_enabled": settings.LLM_ENABLED
    }

# Include routers
app.include_router(remediation_router, prefix="/remediation", tags=["remediation"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8004,
        reload=settings.DEBUG,
        ssl_keyfile=settings.SSL_KEYFILE,
        ssl_certfile=settings.SSL_CERTFILE
    )

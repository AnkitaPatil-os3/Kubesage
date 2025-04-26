from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import settings, limiter
from app.routes import ai_router
from app.database import create_db_and_tables
from app.logger import logger
import os

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI Service for Kubernetes command generation and execution",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Allow frontend requests
origins = [
    "https://10.0.34.168:9980",
    "https://localhost:9980"  # Backend API
]


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ai_router, prefix=settings.API_PREFIX)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting AI Service")
    create_db_and_tables()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down AI Service")

@app.get("/", tags=["Health"])
async def root():
    return {"message": "AI Service is running"}

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True ,  ssl_keyfile="key.pem", ssl_certfile="cert.pem")

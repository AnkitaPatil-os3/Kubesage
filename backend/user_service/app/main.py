import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware  # Import CORSMiddleware
from app.routes import auth_router, user_router, api_key_router
from app.database import create_db_and_tables
from app.consumer import start_consumers
from app.logger import logger
from app.background_tasks import cleanup_expired_tokens_task, cleanup_inactive_sessions_task
import uvicorn
import uuid, ssl

# Background tasks
background_tasks = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background tasks
    cleanup_task = asyncio.create_task(cleanup_expired_tokens_task())
    inactive_cleanup_task = asyncio.create_task(cleanup_inactive_sessions_task())
    
    background_tasks.extend([cleanup_task, inactive_cleanup_task])
    
    yield
    
    # Cancel background tasks on shutdown
    for task in background_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="User Service API",
    description="Enhanced user authentication with multi-session support",
    version="2.0.0",
    lifespan=lifespan
)

# Allow frontend requests


# ✅ Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins, or specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()
    # Start message consumers
    start_consumers()
    logger.info("User service started")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/users", tags=["Users"])
app.include_router(api_key_router, prefix="/api-keys", tags=["API Keys"])  


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True , ssl_keyfile="key.pem", ssl_certfile="cert.pem")


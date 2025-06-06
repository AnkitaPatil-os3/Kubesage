from fastapi import FastAPI, Request, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.database import create_db_and_tables
from app.logger import logger
import time
from typing import Optional
import uvicorn
import os
 
app = FastAPI(
    title="Chat Service",
    description="Microservice for managing chat interactions with AI for Kubernetes analysis",
    version="0.1.0"
)
 
# Allow frontend requests
origins = [
    "*",  # Allow all origins for development
]
 
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
 
# Include routers
app.include_router(router)
 
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Chat Service")
    create_db_and_tables()
    logger.info("Database tables created")
 
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Chat Service")
 
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
 
@app.get("/")
async def root():
    return {
        "service": "Chat Service",
        "version": "0.1.0",
        "status": "running"
    }
 
# Get current session (useful for frontend to know the current session)
@app.get("/current-session")
async def get_current_session(session_id: Optional[str] = Cookie(None)):
    """Get the current session ID from cookie."""
    from app.services import get_chat_session
    
    if not session_id:
        return {"session_id": None, "status": "no_session"}
    
    session = await get_chat_session(None, session_id)
    if not session:
        return {"session_id": None, "status": "invalid_session"}
    
    return {"session_id": session_id, "status": "active"}
 
# Add this section to run the app with HTTPS when executed directly
if __name__ == "__main__":
    import os
    
    # Get the absolute path to the certificate files
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ssl_keyfile = os.path.join(base_dir, "server.key")
    ssl_certfile = os.path.join(base_dir, "server.crt")
    
    if os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile):
        logger.info(f"Starting server with HTTPS using certificates at {ssl_keyfile} and {ssl_certfile}")
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8443,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile
        )
    else:
        logger.warning(f"SSL certificates not found at {ssl_keyfile} and {ssl_certfile}, starting without HTTPS")
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
 
 
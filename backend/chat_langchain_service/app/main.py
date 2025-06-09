from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from app.config import settings
from app.database import create_db_and_tables
from app.routes import router
from app.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Chat LangChain Service...")
    try:
        create_db_and_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # Test LangChain connection
    try:
        from app.langchain_service import get_non_streaming_llm
        llm = get_non_streaming_llm()
        test_response = await llm.ainvoke("Hello")
        logger.info("LangChain connection test successful")
    except Exception as e:
        logger.error(f"LangChain connection test failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Chat LangChain Service...")

# Create FastAPI app
app = FastAPI(
    title="KubeSage Chat LangChain Service",
    description="""
    Chat service with LangChain integration for Kubernetes assistance.
    
    Features:
    - Context-aware conversations with session management
    - LangChain-powered AI responses with tool calling
    - Kubernetes event fetching and kubectl command execution
    - Streaming and non-streaming responses
    - Chat history and session management
    - User authentication and authorization
    """,
    version="1.0.0",
    lifespan=lifespan,
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

# Include routes
app.include_router(router, prefix="/api/v1", tags=["chat"])

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "chat-langchain-service",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "KubeSage Chat LangChain Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8003,
        reload=settings.DEBUG,
        log_level="info"
    )
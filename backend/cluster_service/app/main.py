from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.logger import logger
from app.routes import router
from app.rabbitmq import connect_to_rabbitmq, connection, channel
from app.websocket_client import cleanup_connections
import ssl

app = FastAPI(
    title="Cluster Service",
    description="Kubernetes cluster management service with on-demand namespace queries",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes with v3.0 prefix
app.include_router(router, prefix="/api/v3.0")

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    try:
        # Connect to RabbitMQ
        if connect_to_rabbitmq():
            logger.info("RabbitMQ connection initialization started")
        else:
            logger.error("Failed to initialize RabbitMQ connection")
        
        logger.info("Cluster Service started successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    try:
        # Clean up WebSocket connections
        await cleanup_connections()
        logger.info("WebSocket connections cleaned up")
        
        # Clean up RabbitMQ connections
        if channel and not channel.is_closed:
            channel.close()
            logger.info("RabbitMQ channel closed")
        
        if connection and not connection.is_closed:
            connection.close()
            logger.info("RabbitMQ connection closed")
        
        logger.info("Cluster Service stopped")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    if settings.USE_SSL:
        # SSL configuration for production
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(settings.SSL_CERTFILE, settings.SSL_KEYFILE)
        
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            ssl_keyfile=settings.SSL_KEYFILE,
            ssl_certfile=settings.SSL_CERTFILE,
            reload=settings.DEBUG
        )
    else:
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG
        )

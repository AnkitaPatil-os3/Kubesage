from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from .config import limiter, logger
from .auth import verify_api_key
from .routers import commands, health
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Kubectl NLP Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # List of allowed origins (can use ["*"] to allow all)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Setup middleware and exception handlers
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Include routers
app.include_router(commands.router)
app.include_router(health.router)

# Prometheus instrumentation
Instrumentator().instrument(app).expose(app)


if __name__ == "__main__":
    import uvicorn
    import os.path
    from .config import PORT, HOST, LOG_LEVEL
    
    # SSL configuration
    ssl_keyfile = os.getenv("SSL_KEYFILE", "key.pem")
    ssl_certfile = os.getenv("SSL_CERTFILE", "cert.pem")
    
    # Check if certificate files exist
    if not os.path.isfile(ssl_keyfile) or not os.path.isfile(ssl_certfile):
        logger.warning(f"SSL certificate files not found: {ssl_keyfile} or {ssl_certfile}")
        logger.warning("Starting server without HTTPS")
        logger.info(f"Starting Uvicorn server on {HOST}:{PORT}")
        uvicorn.run("app.main:app", 
                    host=HOST, 
                    port=PORT, 
                    reload=False, 
                    log_level=LOG_LEVEL.lower())
    else:
        logger.info(f"Starting Uvicorn server with HTTPS on {HOST}:{PORT}")
        logger.info(f"Using SSL key: {ssl_keyfile}, cert: {ssl_certfile}")
        uvicorn.run("app.main:app", 
                    host=HOST, 
                    port=PORT, 
                    reload=False, 
                    log_level=LOG_LEVEL.lower(),
                    ssl_keyfile=ssl_keyfile,
                    ssl_certfile=ssl_certfile)
        


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading

from app.routes import k8sgpt_router
from app.database import create_db_and_tables
from app.queue import rabbitmq_client
from app.logger import logger
from app.redis_setup import setup_redis

app = FastAPI(title="KubeSage K8sGPT Operations Service")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router
app.include_router(k8sgpt_router, tags=["K8sGPT Operations"])

@app.on_event("startup")
def on_startup():
    logger.info("Starting K8sGPT Operations Service")
    create_db_and_tables()
    setup_redis()
    
    # Start RabbitMQ consumer in a separate thread
    def start_rabbitmq_consumer():
        try:
            rabbitmq_client.start_consuming()
        except Exception as e:
            logger.error(f"RabbitMQ consumer error: {str(e)}")
    
    threading.Thread(target=start_rabbitmq_consumer, daemon=True).start()

@app.on_event("shutdown")
def on_shutdown():
    logger.info("Shutting down K8sGPT Operations Service")
    rabbitmq_client.close()

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem"
    )
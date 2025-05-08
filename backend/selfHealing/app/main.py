from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading
from app.queue import RabbitMQClient
import pika
import os

from app.routes import self_healing_router
from app.database import create_db_and_tables
from app.queue import rabbitmq_client
from app.logger import logger
from app.redis_setup import setup_redis
from app.agents.analyzer import AnalyzerAgent
from app.agents.reasoner import ReasonerAgent
from app.agents.enforcer import EnforcerAgent

app = FastAPI(title="KubeSage Self-Healing Service")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router
app.include_router(
    self_healing_router, tags=["Self-Healing"])

# Initialize agents
analyzer = None
reasoner = None
enforcer = None



# Initialize RabbitMQ client
rabbitmq_params = pika.ConnectionParameters(
    host=os.getenv("RABBITMQ_HOST", "localhost"),
    port=int(os.getenv("RABBITMQ_PORT", "5672")),
    credentials=pika.PlainCredentials(
        username=os.getenv("RABBITMQ_USER", "guest"),
        password=os.getenv("RABBITMQ_PASSWORD", "guest")
    ),
    heartbeat=60,
    blocked_connection_timeout=30
)
rabbitmq_client = RabbitMQClient(rabbitmq_params)





@app.on_event("startup")
def on_startup():
    logger.info("Starting Self-Healing Service")
    
    # Initialize database
    create_db_and_tables()
    
    # Initialize Redis
    setup_redis()
    
    # Initialize agents
    global analyzer, reasoner, enforcer
    try:
        analyzer = AnalyzerAgent()
        reasoner = ReasonerAgent()
        enforcer = EnforcerAgent()
        logger.info("All agents initialized successfully")
    except Exception as e:
        logger.critical(f"Failed to initialize agents: {str(e)}")
        
    # Start RabbitMQ consumer
    def process_message(ch, method, properties, body):
        # Your message processing logic here
        pass
    
    rabbitmq_client.start_consuming("self-healing-queue", process_message)
    
    # Start RabbitMQ consumer in a separate thread
    def start_rabbitmq_consumer():
        try:
            rabbitmq_client.start_consuming()
        except Exception as e:
            logger.error(f"RabbitMQ consumer error: {str(e)}")
    
    threading.Thread(target=start_rabbitmq_consumer, daemon=True).start()

@app.on_event("shutdown")
def on_shutdown():
    logger.info("Shutting down Self-Healing Service")
    rabbitmq_client.close()

@app.get("/health")
def health_check():
    """Health check endpoint"""
    global analyzer, reasoner, enforcer
    
    # Check if all agents are initialized
    agents_ready = all([analyzer, reasoner, enforcer])
    
    if agents_ready:
        return {"status": "healthy", "message": "Self-Healing Service is running"}
    else:
        return {
            "status": "unhealthy", 
            "message": "One or more agents failed to initialize",
            "agents": {
                "analyzer": analyzer is not None,
                "reasoner": reasoner is not None,
                "enforcer": enforcer is not None
            }
        }

if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.getenv("PORT", "8005"))
    host = os.getenv("HOST", "0.0.0.0")
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    # Check if SSL certificates exist
    ssl_keyfile = os.getenv("SSL_KEYFILE", "key.pem")
    ssl_certfile = os.getenv("SSL_CERTFILE", "cert.pem")
    
    if os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile):
        logger.info(f"Starting HTTPS server on {host}:{port}")
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            log_level=log_level,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile
        )
    else:
        logger.info(f"Starting HTTP server on {host}:{port}")
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            log_level=log_level
        )

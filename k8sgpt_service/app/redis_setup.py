import redis
from app.config import settings
from app.logger import logger

# Redis client
redis_client = None

def setup_redis():
    """Setup Redis connection"""
    global redis_client
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        # Test the connection
        redis_client.ping()
        logger.info("Connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        redis_client = None

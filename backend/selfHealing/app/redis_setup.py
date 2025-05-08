import redis
from app.config import settings
from app.logger import logger

# Initialize Redis client
redis_client = None

def setup_redis():
    """Set up Redis connection"""
    global redis_client
    
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=0,  # Use DB 0 for queue, DB 1 for cache
            decode_responses=False
        )
        # Test connection
        redis_client.ping()
        logger.info("Redis connection established")
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {str(e)}")
        redis_client = None
        return False

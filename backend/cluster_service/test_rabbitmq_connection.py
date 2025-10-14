#!/usr/bin/env python3
"""
Test script to verify RabbitMQ connection
"""
import asyncio
import time
import sys
import os

# Add the app directory to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.rabbitmq import connect_to_rabbitmq, is_rabbitmq_ready, connection, channel
from app.logger import logger

async def test_rabbitmq_connection():
    """Test RabbitMQ connection"""
    logger.info("Starting RabbitMQ connection test...")
    
    # Initialize connection
    if connect_to_rabbitmq():
        logger.info("Connection initialization started")
    else:
        logger.error("Failed to initialize connection")
        return False
    
    # Wait for connection to establish
    max_wait = 10  # seconds
    waited = 0
    
    while waited < max_wait:
        if is_rabbitmq_ready():
            logger.info("RabbitMQ connection is ready!")
            return True
        
        await asyncio.sleep(1)
        waited += 1
        logger.info(f"Waiting for connection... ({waited}/{max_wait})")
    
    logger.error("Connection not ready after waiting")
    return False

if __name__ == "__main__":
    success = asyncio.run(test_rabbitmq_connection())
    if success:
        print("✅ RabbitMQ connection test passed")
        sys.exit(0)
    else:
        print("❌ RabbitMQ connection test failed")
        sys.exit(1)

import logging
import sys
from app.config import settings

# Configure logger
logger = logging.getLogger("chat_service")
logger.setLevel(getattr(logging, settings.LOG_LEVEL))

# Create console handler
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(getattr(logging, settings.LOG_LEVEL))

# Create formatter
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(handler)

# Prevent duplicate log messages
logger.propagate = False

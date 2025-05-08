import logging
import os
from datetime import datetime
from pythonjsonlogger import jsonlogger

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure logger
logger = logging.getLogger("selfHealing")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# File handler with timestamp in filename
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
file_handler = logging.FileHandler(f"logs/selfHealing_{current_time}.log")
file_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# JSON formatter for structured logging
json_handler = logging.StreamHandler()
json_formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
json_handler.setFormatter(json_formatter)
logger.addHandler(json_handler)

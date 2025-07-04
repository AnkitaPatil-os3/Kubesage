import logging
import sys
from app.config import settings

# Configure logger
logger = logging.getLogger("kubesage_langgraph_chat")
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

# Add colored logging for better visibility
class ColoredFormatter(logging.Formatter):
    """Colored log formatter."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

# Use colored formatter if in debug mode
if settings.DEBUG:
    colored_formatter = ColoredFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(colored_formatter)

# Export logger
__all__ = ['logger']

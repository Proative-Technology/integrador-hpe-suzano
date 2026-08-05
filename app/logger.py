from loguru import logger
import logging
import sys
from app.config import settings

# Remove default handlers
logger.remove()

if settings.debug:
# Configure Loguru
    logger.add(
        sys.stdout,  # Log to console
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG",  # Set log level to DEBUG
    )

logger.add(
    settings.log_file,  # Log to file
    rotation="10 MB",  # Rotate logs when they reach 10MB
    retention=10,  # Retain logs for 10  files
    compression="zip",  # Compress old logs
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

# Intercept standard logging (Uvicorn/Gunicorn)
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level
        level = logger.level(record.levelname).name if record.levelname in logger._core.levels else "INFO"
        logger.log(level, record.getMessage())

intercept_handler = InterceptHandler()

for log_name in (
    "uvicorn",
    "uvicorn.access",
    "uvicorn.error",
    "gunicorn",
    "gunicorn.access",
    "gunicorn.error",
):
    standard_logger = logging.getLogger(log_name)
    standard_logger.handlers = [intercept_handler]
    standard_logger.propagate = False

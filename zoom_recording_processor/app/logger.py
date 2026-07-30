import logging
import sys
from app.config import Config

def setup_logger(name: str) -> logging.Logger:
    """
    Create a logger with consistent formatting.
    
    Logs to stdout for CloudWatch Logs to capture.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, Config.LOG_LEVEL))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Handler - output to stdout (CloudWatch captures this)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, Config.LOG_LEVEL))
    
    # Formatter - structured format for easy parsing
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger
"""
Logging configuration for Robot Dashboard
Import and use this at the top of dashboard.py and other modules
"""

import sys
import logging
from logging.handlers import RotatingFileHandler
import os


def setup_logging(
    log_level=logging.DEBUG,
    log_file=None,
    console_output=True,
    include_timestamp=True
):
    """
    Configure logging for the robot dashboard
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file (for direct file logging)
        console_output: Whether to output to console/stdout
        include_timestamp: Whether to include timestamp in log format
    
    Returns:
        Logger instance
    """
    
    # Create logger
    logger = logging.getLogger("robot")
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers = []
    
    # Create formatter
    if include_timestamp:
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)8s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        formatter = logging.Formatter(
            '[%(levelname)8s] %(name)s - %(message)s'
        )
    
    # Console handler (stdout)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler (if specified - for local development)
    if log_file:
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Pre-configured logger instance
log = setup_logging()


# Convenience functions for common logging patterns
def log_startup(app_name, version=None):
    """Log application startup"""
    log.info("=" * 60)
    log.info(f"{app_name} Starting...")
    if version:
        log.info(f"Version: {version}")
    log.info("=" * 60)


def log_shutdown(app_name):
    """Log application shutdown"""
    log.info("=" * 60)
    log.info(f"{app_name} Shutting Down")
    log.info("=" * 60)


def log_exception(msg="Exception occurred"):
    """Log an exception with full traceback"""
    log.exception(msg)


# Example usage in your dashboard.py:
"""
from logger_config import log, log_startup, log_shutdown, log_exception

try:
    log_startup("Robot Dashboard", "1.0")
    
    log.info("Initializing hardware...")
    log.debug("GPIO pins configured")
    log.warning("Battery level low: 15%")
    
    # Your dashboard code here
    
except Exception as e:
    log_exception("Fatal error in dashboard")
    raise
finally:
    log_shutdown("Robot Dashboard")
"""

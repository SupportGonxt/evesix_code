"""
Logging configuration for Robot Dashboard
Import and use this at the top of dashboard.py and other modules.

Sub-loggers (all children of "robot", inherit its handlers automatically):
  robot.hardware  — GPIO reads/writes, relay, sensor, DB connections
  robot.thread    — Thread start/stop/health events
  robot.cycle     — Cycle step progression (WARMUP / CYCLE / MOTION / SUCCESS)
  robot.watchdog  — Watchdog heartbeat and freeze alerts
"""

import sys
import logging
from logging.handlers import RotatingFileHandler
import os

# Production safety: if a log handler itself throws an exception (e.g. disk
# full, permission error), Python swallows it silently instead of propagating
# it to the application. The dashboard must never crash due to logging.
logging.raiseExceptions = False


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
    
    # File handler — writes structured logs directly to disk.
    # RotatingFileHandler calls flush() after every emit, so no records are
    # lost on abrupt power-off (unlike stdout which is block-buffered).
    # Keeps up to 5 × 5 MB = 25 MB of history on disk.
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,   # 5 MB per file
            backupCount=5,               # robot_monitor.log.1 … .5
            delay=False,                 # open the file immediately on startup
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Pre-configured logger instance
log = setup_logging()

# ── Sub-loggers for hardware-monitoring subsystems ────────────────────────────
# Import these directly in any module that needs them, e.g.:
#   from logger_config import hw_log, thread_log, cycle_log, wd_log
#
# They automatically inherit the root "robot" logger's handlers, so all
# output lands in the same log file / console stream.
hw_log     = logging.getLogger("robot.hardware")
thread_log = logging.getLogger("robot.thread")
cycle_log  = logging.getLogger("robot.cycle")
wd_log     = logging.getLogger("robot.watchdog")


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

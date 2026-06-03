import logging
import logging.handlers
import os
import sys
import json
from datetime import datetime
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "duration"):
            log_data["duration_ms"] = record.duration
        return json.dumps(log_data)


def setup_logging(log_level: str = None, log_file: str = None) -> logging.Logger:
    """
    Configure centralized logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). Defaults to env var or INFO.
        log_file: Path to log file. Defaults to logs/insightflow.log.
    
    Returns:
        Configured logger instance.
    """
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    if log_file is None:
        log_file = os.getenv("LOG_FILE", "logs/insightflow.log")

    # Create logs directory if needed
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create root logger
    logger = logging.getLogger("insightflow")
    logger.setLevel(getattr(logging, log_level))

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler (human-readable)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (JSON for structured logging)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(getattr(logging, log_level))
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module."""
    return logging.getLogger(f"insightflow.{name}")

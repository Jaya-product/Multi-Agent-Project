"""Structured logging and graph node trace capture for observability."""

import logging
import sys
import time
from typing import Dict, Any, Optional


def get_logger(name: str = "dubai_travel_agent") -> logging.Logger:
    """Return a configured logger with standard formatting."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_node_trace(
    node_name: str,
    latency_seconds: float,
    status: str = "SUCCESS",
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a structured snapshot dict for UI trace inspection."""
    return {
        "node_name": node_name,
        "timestamp": time.time(),
        "latency_seconds": round(latency_seconds, 3),
        "status": status,
        "details": details or {},
    }

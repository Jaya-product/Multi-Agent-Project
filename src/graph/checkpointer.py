"""Checkpointing configuration for state snapshots and execution replay."""

from typing import Optional, Any
from langgraph.checkpoint.memory import MemorySaver


def get_checkpointer(checkpointer_type: str = "memory") -> Any:
    """Return configured checkpointer instance for state persistence.
    
    Args:
        checkpointer_type: Type of checkpointer ('memory').
    
    Returns:
        Instance of MemorySaver (or custom checkpointer).
    """
    if checkpointer_type == "memory":
        return MemorySaver()
    else:
        # Default in-memory checkpointer
        return MemorySaver()

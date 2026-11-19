"""Validation and review verdict models."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ReviewResult(BaseModel):
    """Output from deterministic rule engine and QA review."""

    approved: bool
    violations: List[str] = Field(default_factory=list)
    revision_instructions: Optional[str] = None
    iteration: int = Field(default=1, ge=1)

"""Resilience error handlers, schema repair, and retry decorators."""

import json
import re
from typing import Any, Dict, Optional, Callable
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


def safe_json_parse(raw_content: Any) -> Dict[str, Any]:
    """Parse JSON string, handling Markdown code fences and trailing commas."""
    if isinstance(raw_content, dict):
        return raw_content

    text = str(raw_content).strip()

    # Extract JSON inside markdown fences if present
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback regex search for outer braces
        brace_match = re.search(r"(\{[\s\S]*\})", text)
        if brace_match:
            try:
                return json.loads(brace_match.group(1))
            except Exception:
                pass

        raise ValueError(f"Failed to parse valid JSON payload from text:\n{text[:300]}")


def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 8.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """Tenacity retry decorator with exponential backoff for transient API faults."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        reraise=True,
    )

import json
import re
from typing import Any


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences that LLMs sometimes add."""
    text = (text or "").strip()
    match = re.search(r"```(?:json|sql)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def safe_parse_json(text: str) -> Any:
    cleaned = strip_code_fences(text)
    return json.loads(cleaned)


def format_number(n: float) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(round(n, 2))


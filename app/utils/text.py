"""Text normalization helpers."""

from __future__ import annotations

import json
from typing import Any


def normalize_text(value: Any, joiner: str = "\n") -> str:
    """Coerce mixed types into a safe, displayable string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except Exception:
            return value.decode("utf-8", errors="replace")
    if isinstance(value, (list, tuple, set)):
        parts: list[str] = []
        for item in value:
            text = normalize_text(item, joiner=joiner).strip()
            if text:
                parts.append(text)
        return joiner.join(parts)
    if isinstance(value, dict):
        try:
            return json.dumps(value, ensure_ascii=True)
        except Exception:
            return str(value)
    return str(value)


def normalize_job_data(job_data: dict | None) -> dict:
    """Normalize common job_data text fields to strings."""
    if not job_data:
        return job_data or {}

    normalized = dict(job_data)
    for key in (
        "job_title",
        "company_name",
        "job_description",
        "requirements",
        "location",
        "team",
        "employment_type",
    ):
        if key in normalized:
            normalized[key] = normalize_text(normalized.get(key))
    return normalized

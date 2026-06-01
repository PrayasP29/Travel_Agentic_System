"""Deterministic conversation helper for missing trip fields."""

from __future__ import annotations

from typing import Any, Mapping

REQUIRED_FIELDS = ("origin", "destination", "event_date")

_FIELD_QUESTIONS = {
    "origin": "Where are you starting from?",
    "destination": "Where are you traveling to?",
    "event_date": "What is the trip or event date? (YYYY-MM-DD)",
}


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def detect_missing_fields(state: Mapping[str, Any]) -> list[str]:
    """Return required fields that are missing from the state."""
    missing: list[str] = []
    for field in REQUIRED_FIELDS:
        if _is_missing(state.get(field)):
            missing.append(field)
    return missing


def next_question(missing_fields: list[str]) -> str | None:
    """Return the next question to ask based on missing fields."""
    if not missing_fields:
        return None
    return _FIELD_QUESTIONS.get(missing_fields[0])


def conversation_status(state: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate conversation readiness without using LLMs."""
    missing_fields = detect_missing_fields(state)
    return {
        "missing_fields": missing_fields,
        "next_question": next_question(missing_fields),
        "ready": not missing_fields,
    }

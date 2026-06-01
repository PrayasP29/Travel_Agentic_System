"""Helpers for building TripPlannerState from parsed requests."""

from __future__ import annotations

from typing import Any, Mapping

from state.trip_state import TripPlannerState


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if text.lower() in {"none", "null", "n/a", "unknown"}:
        return ""
    return text


def _normalize_travelers(value: Any) -> int:
    if value is None or value == "":
        return 1
    if isinstance(value, bool):
        raise ValueError("travelers must be a positive integer.")
    if isinstance(value, int):
        travelers = value
    elif isinstance(value, float) and value.is_integer():
        travelers = int(value)
    elif isinstance(value, str):
        if not value.strip().isdigit():
            raise ValueError("travelers must be a positive integer.")
        travelers = int(value.strip())
    else:
        raise ValueError("travelers must be a positive integer.")

    if travelers < 1:
        raise ValueError("travelers must be a positive integer.")
    return travelers


def build_trip_state(parsed_request: Mapping[str, Any]) -> TripPlannerState:
    """Convert a parsed request into the TripPlannerState structure."""
    if parsed_request is None:
        raise ValueError("parsed_request is required to build trip state.")

    return {
        "origin": _normalize_text(parsed_request.get("origin")),
        "destination": _normalize_text(parsed_request.get("destination")),
        "travelers": _normalize_travelers(parsed_request.get("travelers")),
        "venue": _normalize_text(parsed_request.get("venue")),
        "event_date": _normalize_text(parsed_request.get("event_date")),
        "errors": [],
    }

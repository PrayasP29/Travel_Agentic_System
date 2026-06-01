"""Request parser agent for natural language trip requests."""

from __future__ import annotations

import json
import re
from typing import Any


_WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def _last_message_content(response: dict) -> str:
    """Extract the final message content from a LangChain agent response."""
    messages = response.get("messages", [])
    if not messages:
        return ""
    return getattr(messages[-1], "content", "") or ""


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if text.lower() in {"none", "null", "n/a", "unknown"}:
        return ""
    return text


def _normalize_travelers(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if not text:
            return None
        if text.isdigit():
            return int(text)
        return _WORD_NUMBERS.get(text)
    return None


def _extract_json_payload(text: str) -> dict:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        candidate = match.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in request parser response.")
        candidate = text[start : end + 1]

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("Unable to parse JSON from request parser response.") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Parsed request payload must be a JSON object.")

    return parsed


def request_parser_agent(user_request: str) -> dict:
    """Parse a natural language trip request into structured fields."""
    if not user_request or not user_request.strip():
        raise ValueError("user_request must be a non-empty string.")

    from langchain.agents import create_agent

    from config.models import get_text_llm

    agent = create_agent(
        model=get_text_llm(),
        tools=[],
        system_prompt=(
            "You are a request parsing agent. Extract structured details from the "
            "user's travel request. Return only JSON with these keys: origin, "
            "destination, travelers, venue, event_date. Use null when a field is "
            "missing. travelers must be an integer. event_date should be "
            "YYYY-MM-DD when available."
        ),
    )

    prompt = (
        "Extract the trip details and respond with JSON only.\n\n"
        f"request: {user_request}"
    )
    response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    payload = _extract_json_payload(_last_message_content(response))

    return {
        "origin": _normalize_text(payload.get("origin")),
        "destination": _normalize_text(payload.get("destination")),
        "travelers": _normalize_travelers(payload.get("travelers")),
        "venue": _normalize_text(payload.get("venue")),
        "event_date": _normalize_text(payload.get("event_date")),
    }

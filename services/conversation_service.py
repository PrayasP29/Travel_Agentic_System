"""Service layer for multi-turn trip planning conversations."""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from agents.conversation_agent import conversation_status
from agents.request_parser_agent import request_parser_agent
from services.trip_planner_service import plan_trip
from utils.state_builder import build_trip_state

_GRAPH_INSTANCE = None


async def _get_graph():
    global _GRAPH_INSTANCE
    if _GRAPH_INSTANCE is None:
        from graph.trip_graph import build_trip_graph

        _GRAPH_INSTANCE = await build_trip_graph()
    return _GRAPH_INSTANCE


def _generate_thread_id() -> str:
    return f"conversation_{uuid.uuid4().hex}"


def _empty_state() -> dict[str, Any]:
    return {
        "origin": "",
        "destination": "",
        "event_date": "",
        "travelers": 1,
        "venue": "",
        "errors": [],
        "status": "collecting",
    }


def _merge_state(current: Mapping[str, Any], updates: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(current)
    for field in ("origin", "destination", "venue", "event_date"):
        value = updates.get(field)
        if isinstance(value, str) and value.strip():
            merged[field] = value.strip()

    travelers = updates.get("travelers")
    if isinstance(travelers, int) and travelers > 0:
        merged["travelers"] = travelers

    merged.setdefault("errors", [])
    return merged


async def _save_state(thread_id: str, state: Mapping[str, Any]) -> None:
    graph = await _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    if hasattr(graph, "update_state"):
        graph.update_state(config, dict(state))
        return
    raise RuntimeError("Graph does not support update_state for checkpointing.")


async def _load_state(thread_id: str) -> dict[str, Any]:
    graph = await _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    if snapshot is None:
        return _empty_state()
    values = snapshot.values if hasattr(snapshot, "values") else snapshot
    if not values:
        return _empty_state()
    return dict(values)


def _compose_request(state: Mapping[str, Any]) -> str:
    parts = []
    origin = state.get("origin")
    destination = state.get("destination")
    event_date = state.get("event_date")
    travelers = state.get("travelers")
    venue = state.get("venue")

    if origin and destination:
        parts.append(f"Plan a trip from {origin} to {destination}")
    elif destination:
        parts.append(f"Plan a trip to {destination}")
    elif origin:
        parts.append(f"Plan a trip from {origin}")
    else:
        parts.append("Plan a trip")

    if event_date:
        parts.append(f"on {event_date}")
    if travelers:
        parts.append(f"for {travelers} traveler{'s' if travelers != 1 else ''}")
    if venue:
        parts.append(f"visiting {venue}")

    return " ".join(parts).strip()


async def _advance_conversation(thread_id: str, state: dict[str, Any]) -> dict[str, Any]:
    status = conversation_status(state)
    if not status["ready"]:
        state["status"] = "collecting"
        await _save_state(thread_id, state)
        return {
            "thread_id": thread_id,
            "status": "collecting",
            "missing_fields": status["missing_fields"],
            "next_question": status["next_question"],
            "state": state,
        }

    if state.get("status") == "completed":
        return {
            "thread_id": thread_id,
            "status": "completed",
            "missing_fields": [],
            "next_question": None,
            "state": state,
        }

    request_text = _compose_request(state)
    state["status"] = "planning"
    await _save_state(thread_id, state)
    plan_result = await plan_trip(request_text)
    
    # Store returned graph result into conversation["state"]
    if isinstance(plan_result, dict):
        state.update(plan_result)
        
    state["status"] = "completed"
    await _save_state(thread_id, state)

    return {
        "thread_id": thread_id,
        "status": "completed",
        "missing_fields": [],
        "next_question": None,
        "state": state,
        "plan_result": plan_result,
    }



async def start_conversation(user_message: str) -> dict[str, Any]:
    """Start a multi-turn trip planning conversation."""
    if not user_message or not user_message.strip():
        raise ValueError("user_message must be a non-empty string.")

    thread_id = _generate_thread_id()
    parsed = request_parser_agent(user_message)
    state = build_trip_state(parsed)
    state["status"] = "collecting"
    return await _advance_conversation(thread_id, state)


def _normalize_event_date(user_message: str) -> str | None:
    import datetime
    import re
    text = user_message.strip()
    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if match:
        return match.group(0)
    cleaned = re.sub(r"\b(\d+)(st|nd|rd|th)\b", r"\1", text, flags=re.IGNORECASE)
    cleaned = cleaned.replace(",", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    formats = [
        "%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y",
        "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"
    ]
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    cleaned_title = cleaned.title()
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(cleaned_title, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    try:
        parsed = request_parser_agent(text)
        val = parsed.get("event_date")
        if val and re.match(r"^\d{4}-\d{2}-\d{2}$", val.strip()):
            return val.strip()
    except Exception:
        pass
    return None


async def continue_conversation(thread_id: str, user_message: str) -> dict[str, Any]:
    """Continue an existing conversation by merging new user input."""
    if not thread_id or not str(thread_id).strip():
        raise ValueError("thread_id must be a non-empty string.")
    if not user_message or not user_message.strip():
        raise ValueError("user_message must be a non-empty string.")

    current_state = await _load_state(thread_id)
    
    from agents.conversation_agent import detect_missing_fields
    missing_fields = detect_missing_fields(current_state)

    if missing_fields:
        target_field = missing_fields[0]
        if target_field == "origin":
            current_state["origin"] = user_message.strip()
        elif target_field == "destination":
            current_state["destination"] = user_message.strip()
        elif target_field == "event_date":
            normalized_date = _normalize_event_date(user_message)
            if normalized_date:
                current_state["event_date"] = normalized_date
        
        updated_state = current_state
    else:
        parsed = request_parser_agent(user_message)
        updated_state = _merge_state(current_state, parsed)

    return await _advance_conversation(thread_id, updated_state)


async def resume_conversation(thread_id: str) -> dict[str, Any]:
    """Resume a previously started conversation."""
    if not thread_id or not str(thread_id).strip():
        raise ValueError("thread_id must be a non-empty string.")

    state = await _load_state(thread_id)
    return await _advance_conversation(thread_id, state)


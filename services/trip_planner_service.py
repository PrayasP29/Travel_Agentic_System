"""Service entrypoints for planning and resuming trips."""

from __future__ import annotations

import uuid
from typing import Any

from agents.request_parser_agent import request_parser_agent
from utils.state_builder import build_trip_state

_GRAPH_INSTANCE = None


def _get_graph():
    global _GRAPH_INSTANCE
    if _GRAPH_INSTANCE is None:
        from graph.trip_graph import build_trip_graph

        _GRAPH_INSTANCE = build_trip_graph()
    return _GRAPH_INSTANCE


def _generate_thread_id() -> str:
    return f"trip_{uuid.uuid4().hex}"


def plan_trip(user_request: str) -> dict[str, Any]:
    """Plan a trip from a natural language request."""
    if not user_request or not user_request.strip():
        raise ValueError("user_request must be a non-empty string.")

    parsed_request = request_parser_agent(user_request)
    state = build_trip_state(parsed_request)
    thread_id = _generate_thread_id()

    print("CLI INITIAL STATE:", state)
    result = _get_graph().invoke(
        state,
        config={
            "configurable": {
                "thread_id": thread_id,
            }
        },
    )

    if isinstance(result, dict):
        payload = dict(result)
        payload["thread_id"] = thread_id
        return payload

    return {"thread_id": thread_id, "result": result}


def resume_trip(thread_id: str) -> dict[str, Any]:
    """Resume an existing trip planning session."""
    if not thread_id or not str(thread_id).strip():
        raise ValueError("thread_id must be a non-empty string.")

    snapshot = _get_graph().get_state(
        {
            "configurable": {
                "thread_id": thread_id,
            }
        }
    )

    if hasattr(snapshot, "values"):
        return snapshot.values

    return snapshot

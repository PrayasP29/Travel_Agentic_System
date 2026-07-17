"""LangGraph workflow for the multi-agent trip planner."""

import inspect
import time

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from agents.coordinator import coordinator_agent
from agents.flight_agent import flight_agent
from agents.hotel_agent import hotel_agent
from agents.itinerary_agent import itinerary_agent
from agents.local_agent import local_agent
from agents.search_agent import search_agent
from agents.supervisor_agent import supervisor_agent
from agents.weather_agent import weather_agent
from memory.sqlite_checkpoint import get_checkpointer
from state.trip_state import TripPlannerState
from utils.execution_log import logger as exec_log

_NODE_LABELS = {
    "coordinator_agent": "Coordinator",
    "supervisor_agent": "Supervisor",
    "flight_agent": "Flight",
    "hotel_agent": "Hotel",
    "weather_agent": "Weather",
    "search_agent": "Search",
    "local_agent": "Local",
    "itinerary_agent": "Itinerary",
}


def _only_changed(state: dict, result: dict) -> dict:
    """Return only keys that are new or differ from the input state.

    Prevents InvalidUpdateError when parallel agents via Send() all
    echo back unchanged LastValue keys (e.g. origin, destination).
    """
    return {k: v for k, v in result.items() if k not in state or state[k] != v}

# Map every possible return value from the routing functions to the
# corresponding registered node name.

_ALL_AGENT_ROUTES = {
    "flight_agent":   "flight_agent",
    "hotel_agent":    "hotel_agent",
    "weather_agent":  "weather_agent",
    "search_agent":   "search_agent",
    "local_agent":    "local_agent",
    "itinerary_agent": "itinerary_agent",
}


_AGENT_PLAN_KEYS = [
    ("run_flight_agent",  "Flight"),
    ("run_hotel_agent",   "Hotel"),
    ("run_weather_agent", "Weather"),
    ("run_search_agent",  "Search"),
    ("run_local_agent",   "Local"),
]


def _route_from_supervisor(state: TripPlannerState):
    """After the supervisor, fan out to all enabled parallel agents via Send(),
    or route directly to itinerary_agent if none are enabled."""
    plan = state.get("execution_plan", {})
    sends = []
    enabled = []
    for key, label in _AGENT_PLAN_KEYS:
        if plan.get(key):
            sends.append(Send(key.replace("run_", ""), state))
            enabled.append(label)
    if enabled:
        exec_log.info("Supervisor routed: %s", ", ".join(f"-> {a}" for a in enabled))
    else:
        exec_log.info("Supervisor routed: -> Itinerary (no parallel agents)")
    if not sends:
        return "itinerary_agent"
    return sends


async def build_trip_graph(*, checkpointer=None):
    """Build and compile the trip-planning graph.

    Args:
        checkpointer: Optional checkpointer override. If None, defaults to
                      AsyncSqliteSaver via get_checkpointer().
    """
    graph = StateGraph(TripPlannerState)

    # ── Nodes ──────────────────────────────────────────────────────────
    # Wrap each agent so only changed keys are returned.  Without this,
    # parallel agents echo back the full state, causing
    # InvalidUpdateError on LastValue keys (origin, destination, …).
    for name, fn in [
        ("coordinator_agent", coordinator_agent),
        ("supervisor_agent", supervisor_agent),
        ("flight_agent", flight_agent),
        ("hotel_agent", hotel_agent),
        ("weather_agent", weather_agent),
        ("search_agent", search_agent),
        ("local_agent", local_agent),
        ("itinerary_agent", itinerary_agent),
    ]:
        def _make(f=fn, _label=None):
            if inspect.iscoroutinefunction(f):
                async def _wrapped(state: dict) -> dict:
                    exec_log.info("%s START", _label)
                    t0 = time.monotonic()
                    try:
                        result = await f(state)
                    except Exception:
                        exec_log.info("%s FAIL (%.2fs)", _label, time.monotonic() - t0)
                        raise
                    exec_log.info("%s COMPLETE (%.2fs)", _label, time.monotonic() - t0)
                    return _only_changed(state, result) if isinstance(result, dict) else result
            else:
                def _wrapped(state: dict) -> dict:
                    exec_log.info("%s START", _label)
                    t0 = time.monotonic()
                    try:
                        result = f(state)
                    except Exception:
                        exec_log.info("%s FAIL (%.2fs)", _label, time.monotonic() - t0)
                        raise
                    exec_log.info("%s COMPLETE (%.2fs)", _label, time.monotonic() - t0)
                    return _only_changed(state, result) if isinstance(result, dict) else result
            return _wrapped
        graph.add_node(name, _make(_label=_NODE_LABELS.get(name, name)))

    # ── Fixed edges ────────────────────────────────────────────────────
    graph.add_edge(START, "coordinator_agent")
    graph.add_edge("coordinator_agent", "supervisor_agent")
    graph.add_edge("itinerary_agent", END)

    # ── Conditional edges from supervisor ──────────────────────────────
    graph.add_conditional_edges(
        "supervisor_agent",
        _route_from_supervisor,
        _ALL_AGENT_ROUTES,
    )

    # ── Fan-in edges: all parallel agents converge on itinerary_agent ──
    graph.add_edge("flight_agent", "itinerary_agent")
    graph.add_edge("hotel_agent", "itinerary_agent")
    graph.add_edge("weather_agent", "itinerary_agent")
    graph.add_edge("search_agent", "itinerary_agent")
    graph.add_edge("local_agent", "itinerary_agent")

    # ── Persistence ────────────────────────────────────────────────────
    if checkpointer is None:
        checkpointer = await get_checkpointer()
    return graph.compile(checkpointer=checkpointer)

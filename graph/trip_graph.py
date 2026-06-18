"""LangGraph workflow for the multi-agent trip planner."""

from langgraph.graph import END, START, StateGraph

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

# Execution order for the specialist agents. The supervisor's execution_plan
# determines which of these actually run — any may be conditionally skipped.
_AGENT_EXECUTION_ORDER = [
    "flight_agent",
    "hotel_agent",
    "weather_agent",
    "search_agent",
    "local_agent",
]

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


def _route_from_supervisor(state: TripPlannerState) -> str:
    """After the supervisor, route to the first agent that needs to run."""
    plan = state.get("execution_plan", {})
    for agent in _AGENT_EXECUTION_ORDER:
        if plan.get(f"run_{agent}", False):
            return agent
    return "itinerary_agent"


def _make_route_after(after: str):
    """Return a routing function that finds the next agent after *after*."""
    def _router(state: TripPlannerState) -> str:
        plan = state.get("execution_plan", {})
        start = _AGENT_EXECUTION_ORDER.index(after) + 1
        for agent in _AGENT_EXECUTION_ORDER[start:]:
            if plan.get(f"run_{agent}", False):
                return agent
        return "itinerary_agent"
    _router.__name__ = f"route_from_{after}"
    return _router


def build_trip_graph():
    """Build and compile the trip-planning graph."""
    graph = StateGraph(TripPlannerState)

    def _run_with_debug(name, fn):
        def _wrapped(state: dict):
            print(f"RUNNING NODE: {name}")
            return fn(state)

        return _wrapped

    # ── Nodes ──────────────────────────────────────────────────────────
    graph.add_node("coordinator_agent",
                   _run_with_debug("coordinator_agent", coordinator_agent))
    graph.add_node("supervisor_agent",
                   _run_with_debug("supervisor_agent", supervisor_agent))
    graph.add_node("flight_agent",
                   _run_with_debug("flight_agent", flight_agent))
    graph.add_node("hotel_agent",
                   _run_with_debug("hotel_agent", hotel_agent))
    graph.add_node("weather_agent",
                   _run_with_debug("weather_agent", weather_agent))
    graph.add_node("search_agent",
                   _run_with_debug("search_agent", search_agent))
    graph.add_node("local_agent",
                   _run_with_debug("local_agent", local_agent))
    graph.add_node("itinerary_agent",
                   _run_with_debug("itinerary_agent", itinerary_agent))

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

    # ── Conditional edges from each specialist agent ───────────────────
    for agent in _AGENT_EXECUTION_ORDER:
        graph.add_conditional_edges(
            agent,
            _make_route_after(agent),
            _ALL_AGENT_ROUTES,
        )

    # ── Persistence ────────────────────────────────────────────────────
    checkpointer = get_checkpointer()
    return graph.compile(checkpointer=checkpointer)

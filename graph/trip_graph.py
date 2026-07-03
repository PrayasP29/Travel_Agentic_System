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


def _route_from_supervisor(state: TripPlannerState):
    """After the supervisor, fan out to all enabled parallel agents via Send(),
    or route directly to itinerary_agent if none are enabled."""
    plan = state.get("execution_plan", {})
    sends = []
    if plan.get("run_flight_agent"):
        sends.append(Send("flight_agent", state))
    if plan.get("run_hotel_agent"):
        sends.append(Send("hotel_agent", state))
    if plan.get("run_weather_agent"):
        sends.append(Send("weather_agent", state))
    if plan.get("run_search_agent"):
        sends.append(Send("search_agent", state))
    if plan.get("run_local_agent"):
        sends.append(Send("local_agent", state))
    if not sends:
        return "itinerary_agent"
    return sends


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


async def build_trip_graph(*, checkpointer=None):
    """Build and compile the trip-planning graph.

    Args:
        checkpointer: Optional checkpointer override. If None, defaults to
                      AsyncSqliteSaver via get_checkpointer().
    """
    graph = StateGraph(TripPlannerState)

    def _run_with_debug(name, fn):
        if inspect.iscoroutinefunction(fn):
            async def _wrapped(state: dict):
                _t_entry = time.perf_counter()
                print(f"[GRAPH] NODE ENTER: {name} t={_t_entry:.3f}")
                _t_fn = time.perf_counter()
                result = await fn(state)
                _t_fn_done = time.perf_counter()
                fn_time = _t_fn_done - _t_fn
                if isinstance(result, dict) and isinstance(state, dict):
                    diff = {k: v for k, v in result.items()
                            if k not in state or state[k] != v}
                else:
                    diff = result
                _t_exit = time.perf_counter()
                overhead = _t_exit - _t_fn_done
                total = _t_exit - _t_entry
                print(f"[GRAPH] NODE EXIT: {name} t={_t_exit:.3f} "
                      f"fn={fn_time:.3f}s overhead={overhead:.3f}s total={total:.3f}s")
                return diff
        else:
            def _wrapped(state: dict):
                _t_entry = time.perf_counter()
                print(f"[GRAPH] NODE ENTER: {name} t={_t_entry:.3f}")
                _t_fn = time.perf_counter()
                result = fn(state)
                _t_fn_done = time.perf_counter()
                fn_time = _t_fn_done - _t_fn
                if isinstance(result, dict) and isinstance(state, dict):
                    diff = {k: v for k, v in result.items()
                            if k not in state or state[k] != v}
                else:
                    diff = result
                _t_exit = time.perf_counter()
                overhead = _t_exit - _t_fn_done
                total = _t_exit - _t_entry
                print(f"[GRAPH] NODE EXIT: {name} t={_t_exit:.3f} "
                      f"fn={fn_time:.3f}s overhead={overhead:.3f}s total={total:.3f}s")
                return diff

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

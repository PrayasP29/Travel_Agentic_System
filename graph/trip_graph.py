"""LangGraph workflow for the multi-agent trip planner."""

from langgraph.graph import END, START, StateGraph

from agents.flight_agent import flight_agent
from agents.hotel_agent import hotel_agent
from agents.itinerary_agent import itinerary_agent
from agents.search_agent import search_agent
from agents.supervisor_agent import supervisor_agent
from agents.weather_agent import weather_agent
from memory.sqlite_checkpoint import get_checkpointer
from state.trip_state import TripPlannerState


def build_trip_graph():
    """Build and compile the trip-planning graph."""
    graph = StateGraph(TripPlannerState)

    def _run_with_debug(name, fn):
        def _wrapped(state: dict):
            print(f"RUNNING NODE: {name}")
            return fn(state)

        return _wrapped

    graph.add_node("supervisor_agent", _run_with_debug("supervisor_agent", supervisor_agent))
    graph.add_node("flight_agent", _run_with_debug("flight_agent", flight_agent))
    graph.add_node("hotel_agent", _run_with_debug("hotel_agent", hotel_agent))
    graph.add_node("weather_agent", _run_with_debug("weather_agent", weather_agent))
    graph.add_node("search_agent", _run_with_debug("search_agent", search_agent))
    graph.add_node("itinerary_agent", _run_with_debug("itinerary_agent", itinerary_agent))

    graph.add_edge(START, "supervisor_agent")
    graph.add_edge("supervisor_agent", "flight_agent")
    graph.add_edge("flight_agent", "hotel_agent")
    graph.add_edge("hotel_agent", "weather_agent")
    graph.add_edge("weather_agent", "search_agent")
    graph.add_edge("search_agent", "itinerary_agent")
    graph.add_edge("itinerary_agent", END)

    checkpointer = get_checkpointer()
    return graph.compile(checkpointer=checkpointer)

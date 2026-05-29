"""LangGraph workflow for the multi-agent trip planner."""

from langgraph.graph import END, StateGraph

from agents.coordinator import coordinator_agent
from agents.flight_agent import flight_agent
from agents.hotel_agent import hotel_agent
from agents.itinerary_agent import itinerary_agent
from agents.search_agent import search_agent
from agents.weather_agent import weather_agent
from state.trip_state import TripState


def build_trip_graph():
    """Build and compile the trip-planning graph."""
    graph = StateGraph(TripState)

    graph.add_node("coordinator", coordinator_agent)
    graph.add_node("flight_agent", flight_agent)
    graph.add_node("hotel_agent", hotel_agent)
    graph.add_node("weather_agent", weather_agent)
    graph.add_node("search_agent", search_agent)
    graph.add_node("itinerary_agent", itinerary_agent)

    graph.set_entry_point("coordinator")
    graph.add_edge("coordinator", "flight_agent")
    graph.add_edge("flight_agent", "hotel_agent")
    graph.add_edge("hotel_agent", "weather_agent")
    graph.add_edge("weather_agent", "search_agent")
    graph.add_edge("search_agent", "itinerary_agent")
    graph.add_edge("itinerary_agent", END)

    return graph.compile()

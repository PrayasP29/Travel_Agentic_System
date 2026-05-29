"""Destination research agent backed by the Tavily search wrapper."""

from tools.tavily_search import web_search


def search_agent(state: dict) -> dict:
    """Collect destination research for itinerary planning."""
    destination = state.get("destination", "")
    query = f"best things to do in {destination} travel itinerary"
    return {"search_results": web_search(query)}

"""Typed state shared by LangGraph nodes."""

from typing import Any, TypedDict


class TripState(TypedDict, total=False):
    """Trip-planning state passed between agents."""

    origin: str
    destination: str
    start_date: str
    end_date: str
    budget: str
    travelers: int
    coordinator_notes: str
    flights: Any
    hotels: Any
    weather: Any
    search_results: list[dict[str, Any]]
    itinerary: str

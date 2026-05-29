"""LangGraph-compatible state definition for the trip planner workflow."""

from typing import TypedDict


class TripState(TypedDict):
    """Shared state passed between LangGraph nodes."""

    # Destination city or area for the trip.
    destination: str

    # Venue, landmark, hotel, or event location relevant to the trip.
    venue: str

    # Date of the event or primary trip activity.
    event_date: str

    # Flight search results or selected flight information.
    flight_details: dict

    # Hotel search results or selected hotel information.
    hotel_details: dict

    # Weather forecast and conditions for the destination/date.
    weather_details: dict

    # Web search results and destination research context.
    search_results: dict

    # Generated trip itinerary text.
    itinerary: str

    # Current workflow status such as pending, running, completed, or failed.
    status: str

    # Error messages collected during graph execution.
    errors: list[str]

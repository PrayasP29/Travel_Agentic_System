"""LangGraph-compatible state definition for the trip planner workflow."""

import operator
from typing import Annotated, TypedDict


class TripPlannerState(TypedDict):
    """Shared state passed between LangGraph nodes."""

    # Origin city or airport.
    origin: str

    # Destination city or area for the trip.
    destination: str

    # Number of travelers.
    travelers: int

    # Venue, landmark, hotel, or event location relevant to the trip.
    venue: str

    # Date of the event or primary trip activity.
    event_date: str

    # Flight search results or selected flight information.
    flight_details: dict

    # Flight agent reasoning and summary notes.
    flight_notes: str

    # Flight agent execution status.
    flight_status: str

    # Hotel search results or selected hotel information.
    hotel_details: dict

    # Hotel agent reasoning and summary notes.
    hotel_notes: str

    # Hotel agent execution status.
    hotel_status: str

    # Weather forecast and conditions for the destination/date.
    weather_details: dict

    # Weather agent reasoning and summary notes.
    weather_notes: str

    # Weather agent execution status.
    weather_status: str

    # Web search results and destination research context.
    search_results: dict

    # Search agent reasoning and summary notes.
    search_notes: str

    # Search agent execution status.
    search_status: str

    # Generated trip itinerary text.
    itinerary: str

    # Final user-facing formatted travel report.
    final_report: str

    # Itinerary generation status.
    itinerary_status: str

    # Supervisor review summary for downstream agents and checkpoint memory.
    supervisor_notes: str

    # Current workflow status such as pending, running, completed, or failed.
    status: str

    # Error messages collected during graph execution. Annotated reducer
    # ensures errors from parallel branches accumulate rather than overwrite.
    errors: Annotated[list[str], operator.add]

    # Booking and pricing state details
    flight_booking_link: str
    hotel_booking_links: Annotated[list[str], operator.add]
    hotel_price_details: Annotated[list[str], operator.add]
    recommended_flight_price: float

    # Supervisor-generated execution plan — which agents to run
    execution_plan: dict

    # Local discovery results (local_agent, optional)
    local_results: dict
    local_notes: str
    local_status: str

"""Coordinator agent for validating and initializing trip-planner state."""


def coordinator_agent(state: dict) -> dict:
    """Validate required inputs and initialize missing state fields."""
    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    if not updated_state.get("destination"):
        errors.append("destination is required.")

    if not updated_state.get("venue"):
        errors.append("venue is required.")

    if not updated_state.get("event_date"):
        errors.append("event_date is required.")

    updated_state.setdefault("flight_details", {})
    updated_state.setdefault("hotel_details", {})
    updated_state.setdefault("weather_details", {})
    updated_state.setdefault("search_results", {})
    updated_state.setdefault("itinerary", "")
    updated_state["errors"] = errors
    updated_state["status"] = "processing"

    return updated_state

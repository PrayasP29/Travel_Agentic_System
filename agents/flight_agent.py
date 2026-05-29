"""Flight-search agent backed by the Kiwi Flight Search MCP server."""

from tools.flight_tools import search_flights


def flight_agent(state: dict) -> dict:
    """Find flight options for the requested trip."""
    flights = search_flights(
        origin=state.get("origin"),
        destination=state.get("destination"),
        start_date=state.get("start_date"),
        end_date=state.get("end_date"),
        travelers=state.get("travelers", 1),
    )
    return {"flights": flights}

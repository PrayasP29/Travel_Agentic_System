"""Hotel-search agent backed by the Agentorist Hotel MCP server."""

from tools.hotel_tools import search_hotels


def hotel_agent(state: dict) -> dict:
    """Find hotel options for the requested destination and dates."""
    hotels = search_hotels(
        destination=state.get("destination"),
        check_in=state.get("start_date"),
        check_out=state.get("end_date"),
        travelers=state.get("travelers", 1),
        budget=state.get("budget"),
    )
    return {"hotels": hotels}

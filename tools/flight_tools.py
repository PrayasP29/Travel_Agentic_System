"""Placeholder flight search tool for future MCP integration."""

from config.settings import settings


def search_flights(
    origin: str | None = None,
    destination: str | None = None,
    event_date: str | None = None,
    travelers: int = 1,
) -> dict:
    """Return dummy flight details until Kiwi MCP is connected."""
    # TODO: Add Kiwi MCP client call here when MCP integration is enabled.
    return {
        "provider": "kiwi",
        "mcp_server_url": settings.kiwi_mcp_server_url,
        "status": "dummy",
        "query": {
            "origin": origin,
            "destination": destination,
            "event_date": event_date,
            "travelers": travelers,
        },
        "flight_options": [
            {
                "airline": "Demo Air",
                "flight_number": "DA-101",
                "departure": "TBD",
                "arrival": "TBD",
                "price": "TBD",
            }
        ],
    }

"""Dummy flight-search tool for the first notebook development phase."""

from config.settings import settings


def search_flights(
    origin: str | None,
    destination: str | None,
    start_date: str | None,
    end_date: str | None,
    travelers: int = 1,
) -> dict:
    """Return deterministic flight data until Kiwi MCP is wired in."""
    return {
        "provider": "kiwi-flight-search-mcp",
        "server_url": settings.kiwi_mcp_server_url,
        "status": "dummy",
        "query": {
            "origin": origin,
            "destination": destination,
            "departure_date": start_date,
            "return_date": end_date,
            "travelers": travelers,
        },
        "options": [
            {
                "airline": "Demo Air",
                "price": "TBD",
                "duration": "TBD",
                "notes": "Replace with Kiwi MCP results later.",
            }
        ],
    }

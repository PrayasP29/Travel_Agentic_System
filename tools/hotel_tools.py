"""Dummy hotel-search tool for the first notebook development phase."""

from config.settings import settings


def search_hotels(
    destination: str | None,
    check_in: str | None,
    check_out: str | None,
    travelers: int = 1,
    budget: str | None = None,
) -> dict:
    """Return deterministic hotel data until Agentorist MCP is wired in."""
    return {
        "provider": "agentorist-hotel-mcp",
        "server_url": settings.agentorist_mcp_server_url,
        "status": "dummy",
        "query": {
            "destination": destination,
            "check_in": check_in,
            "check_out": check_out,
            "travelers": travelers,
            "budget": budget,
        },
        "options": [
            {
                "name": "Demo Stay",
                "price_per_night": "TBD",
                "area": destination or "TBD",
                "notes": "Replace with Agentorist MCP results later.",
            }
        ],
    }

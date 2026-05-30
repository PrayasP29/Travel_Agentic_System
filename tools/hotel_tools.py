"""Placeholder hotel search tool for future MCP integration."""

from config.settings import settings


def search_hotels(
    destination: str | None = None,
    venue: str | None = None,
    event_date: str | None = None,
    travelers: int = 1,
) -> dict:
    """Return dummy hotel details until Agentorist MCP is connected."""
    # TODO: Add Agentorist MCP client call here when MCP integration is enabled.
    return {
        "provider": "agentorist",
        "mcp_server_url": settings.agentorist_mcp_server_url,
        "status": "dummy",
        "query": {
            "destination": destination,
            "venue": venue,
            "event_date": event_date,
            "travelers": travelers,
        },
        "hotel_options": [
            {
                "name": "Demo Stay",
                "address": "Near event venue",
                "price_per_night": "TBD",
                "rating": "TBD",
            }
        ],
    }

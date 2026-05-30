"""Placeholder weather tool for future MCP integration."""

from config.settings import settings


def get_weather(
    destination: str | None,
    event_date: str | None,
) -> dict:
    """Return dummy weather details until Gribstream MCP is connected."""
    # TODO: Add Gribstream MCP client call here when MCP integration is enabled.
    return {
        "provider": "gribstream",
        "mcp_server_url": settings.gribstream_mcp_server_url,
        "status": "dummy",
        "query": {
            "destination": destination,
            "event_date": event_date,
        },
        "weather": {
            "summary": "Weather details unavailable in placeholder mode.",
            "temperature": "TBD",
            "conditions": "TBD",
        },
    }

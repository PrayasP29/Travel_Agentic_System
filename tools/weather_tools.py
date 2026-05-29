"""Dummy weather tool for the first notebook development phase."""

from config.settings import settings


def get_weather_forecast(
    destination: str | None,
    start_date: str | None,
    end_date: str | None,
) -> dict:
    """Return deterministic weather data until Gribstream MCP is wired in."""
    return {
        "provider": "gribstream-weather-mcp",
        "server_url": settings.gribstream_mcp_server_url,
        "status": "dummy",
        "query": {
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
        },
        "forecast": {
            "summary": "Weather placeholder",
            "packing_tip": "Check live conditions before travel.",
            "notes": "Replace with Gribstream MCP results later.",
        },
    }

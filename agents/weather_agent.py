"""Weather agent backed by the Gribstream Weather MCP server."""

from tools.weather_tools import get_weather_forecast


def weather_agent(state: dict) -> dict:
    """Fetch weather context for the destination and travel dates."""
    weather = get_weather_forecast(
        destination=state.get("destination"),
        start_date=state.get("start_date"),
        end_date=state.get("end_date"),
    )
    return {"weather": weather}

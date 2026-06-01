"""LiveDataLink weather tool wrapper for the trip planner."""

from __future__ import annotations

from datetime import date, datetime

from tools.weather_mcp_client import (
    get_air_quality,
    get_current_weather,
    get_weather_forecast,
)

PROVIDER = "livedatalink"
FORECAST_MIN_DAYS = 1
FORECAST_MAX_DAYS = 16


def _parse_event_date(event_date: str) -> date:
    """Parse an event date in YYYY-MM-DD format."""
    return datetime.strptime(event_date, "%Y-%m-%d").date()


def _calculate_forecast_days(event_date: str) -> int:
    """Calculate clamped forecast days between today and the event."""
    target_date = _parse_event_date(event_date)
    delta_days = (target_date - date.today()).days
    if delta_days < FORECAST_MIN_DAYS:
        return FORECAST_MIN_DAYS
    if delta_days > FORECAST_MAX_DAYS:
        return FORECAST_MAX_DAYS
    return delta_days


def get_weather(
    destination: str | None,
    event_date: str | None,
) -> dict:
    """Fetch forecast and air quality for the destination."""
    if not destination:
        return {
            "status": "error",
            "provider": PROVIDER,
            "error": "destination is required.",
        }

    if not event_date:
        current_result = get_current_weather(destination)
        if current_result.get("status") != "success":
            return {
                "status": "error",
                "provider": PROVIDER,
                "error": "Current weather lookup failed.",
                "current_weather": current_result,
            }

        return {
            "status": "success",
            "provider": PROVIDER,
            "current_weather": current_result,
        }

    try:
        days = _calculate_forecast_days(event_date)
    except ValueError as exc:
        return {
            "status": "error",
            "provider": PROVIDER,
            "error": f"Invalid event_date format: {exc}",
        }

    forecast_result = get_weather_forecast(destination, days=days)
    air_quality_result = get_air_quality(destination)

    if (
        forecast_result.get("status") != "success"
        or air_quality_result.get("status") != "success"
    ):
        return {
            "status": "error",
            "provider": PROVIDER,
            "error": "Weather MCP lookup failed.",
            "forecast": forecast_result,
            "air_quality": air_quality_result,
        }

    return {
        "status": "success",
        "provider": PROVIDER,
        "forecast": forecast_result,
        "air_quality": air_quality_result,
    }

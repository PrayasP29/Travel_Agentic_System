"""LiveDataLink weather tool wrapper for the trip planner."""

from __future__ import annotations

import asyncio
from datetime import date, datetime

from tools.weather_mcp_client import (
    get_air_quality,
    get_current_weather,
    get_weather_forecast,
)
from utils.error_categories import classify_error

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


async def _safe_get_air_quality(destination: str) -> dict:
    """Fetch air quality, returning a concise error dict on any failure."""
    try:
        return await get_air_quality(destination)
    except asyncio.TimeoutError:
        return {
            "status": "error",
            "provider": PROVIDER,
            "error": "Air quality request timed out.",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "provider": PROVIDER,
            "error": classify_error(exc, "weather"),
        }


async def get_weather(
    destination: str | None,
    event_date: str | None,
) -> dict:
    """Fetch forecast and air quality for the destination.

    Weather forecast is the primary requirement. Air quality is optional —
    a failure there does not fail the overall weather request.
    """
    if not destination:
        return {
            "status": "error",
            "provider": PROVIDER,
            "error": "destination is required.",
        }

    if not event_date:
        current_result = await get_current_weather(destination)
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

    # Forecast is required — a failure here fails the whole request.
    forecast_result = await get_weather_forecast(destination, days=days)
    if forecast_result.get("status") != "success":
        return {
            "status": "error",
            "provider": PROVIDER,
            "error": "Weather forecast lookup failed.",
            "forecast": forecast_result,
        }

    # Air quality is optional — preserve forecast even when AQI fails.
    air_quality_result = await _safe_get_air_quality(destination)

    return {
        "status": "success",
        "provider": PROVIDER,
        "forecast": forecast_result,
        "air_quality": air_quality_result,
    }
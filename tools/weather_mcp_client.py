"""LiveDataLink MCP client helpers for weather data."""

from __future__ import annotations

import asyncio
import traceback
from typing import Any

from mcp import ClientSession, types
from mcp.client.streamable_http import streamable_http_client

from config.settings import settings
from utils.error_categories import classify_error

PROVIDER = "livedatalink"
DEFAULT_TIMEOUT_SECONDS = 20


def _extract_text(result: Any) -> str:
    """Extract text content from MCP CallToolResult."""
    content = getattr(result, "content", None) or []
    texts: list[str] = []
    for item in content:
        if isinstance(item, types.TextContent):
            texts.append(item.text)
        elif hasattr(item, "text"):
            texts.append(getattr(item, "text"))
        elif isinstance(item, dict) and "text" in item:
            texts.append(str(item["text"]))
    return "\n".join(texts).strip()


def _log_exception_details(exc: BaseException) -> str:
    """Return detailed exception diagnostics."""
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


async def _call_tool(
    tool_name: str, payload: dict, timeout_seconds: int
) -> dict[str, Any]:
    """Connect to MCP server, verify tool availability, and call the tool."""
    async with streamable_http_client(settings.weather_mcp_server_url) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await asyncio.wait_for(session.initialize(), timeout=timeout_seconds)
            tools = await asyncio.wait_for(session.list_tools(), timeout=timeout_seconds)
            tool_names = [tool.name for tool in tools.tools]
            if tool_name not in tool_names:
                raise RuntimeError(
                    f"Tool '{tool_name}' not available. Tools: {tool_names}"
                )
            result = await asyncio.wait_for(
                session.call_tool(tool_name, payload), timeout=timeout_seconds
            )
            return {"tools": tool_names, "result": result}


def _handle_response(tool_name: str, response: dict) -> dict:
    """Normalize MCP response to the standard return format."""
    result = response["result"]
    if getattr(result, "isError", False):
        error_text = _extract_text(result) or "Weather MCP tool failed."
        return {
            "status": "error",
            "provider": PROVIDER,
            "tool_used": tool_name,
            "error": error_text,
            "data": "",
        }

    extracted_text = _extract_text(result)
    if not extracted_text:
        return {
            "status": "error",
            "provider": PROVIDER,
            "tool_used": tool_name,
            "error": "Weather MCP returned no text content.",
            "data": "",
        }

    return {
        "status": "success",
        "provider": PROVIDER,
        "tool_used": tool_name,
        "data": extracted_text,
    }


async def get_current_weather(location: str) -> dict:
    """Fetch current weather conditions via LiveDataLink MCP."""
    if not location:
        return {
            "status": "error",
            "provider": PROVIDER,
            "tool_used": "weather_current",
            "error": "location is required.",
            "data": "",
        }

    payload = {"location": location}

    try:
        response = await _call_tool("weather_current", payload, DEFAULT_TIMEOUT_SECONDS)
        return _handle_response("weather_current", response)
    except asyncio.TimeoutError as exc:
        _log_exception_details(exc)
        return {
            "status": "error",
            "provider": PROVIDER,
            "tool_used": "weather_current",
            "error": classify_error(exc, "weather"),
            "data": "",
        }
    except Exception as exc:
        _log_exception_details(exc)
        return {
            "status": "error",
            "provider": PROVIDER,
            "tool_used": "weather_current",
            "error": classify_error(exc, "weather"),
            "data": "",
        }


async def get_weather_forecast(location: str, days: int = 7) -> dict:
    """Fetch weather forecast via LiveDataLink MCP."""
    if not location:
        return {
            "status": "error",
            "provider": PROVIDER,
            "tool_used": "weather_forecast",
            "error": "location is required.",
            "data": "",
        }

    payload = {"location": location, "days": days}

    try:
        response = await _call_tool("weather_forecast", payload, DEFAULT_TIMEOUT_SECONDS)
        return _handle_response("weather_forecast", response)
    except asyncio.TimeoutError as exc:
        _log_exception_details(exc)
        return {
            "status": "error",
            "provider": PROVIDER,
            "tool_used": "weather_forecast",
            "error": classify_error(exc, "weather"),
            "data": "",
        }
    except Exception as exc:
        _log_exception_details(exc)
        return {
            "status": "error",
            "provider": PROVIDER,
            "tool_used": "weather_forecast",
            "error": classify_error(exc, "weather"),
            "data": "",
        }


async def get_air_quality(location: str) -> dict:
    """Fetch air quality via LiveDataLink MCP."""
    if not location:
        return {
            "status": "error",
            "provider": PROVIDER,
            "tool_used": "air_quality",
            "error": "location is required.",
            "data": "",
        }

    payload = {"location": location}

    try:
        response = await _call_tool("air_quality", payload, DEFAULT_TIMEOUT_SECONDS)
        return _handle_response("air_quality", response)
    except asyncio.TimeoutError as exc:
        _log_exception_details(exc)
        return {
            "status": "error",
            "provider": PROVIDER,
            "tool_used": "air_quality",
            "error": classify_error(exc, "weather"),
            "data": "",
        }
    except Exception as exc:
        _log_exception_details(exc)
        return {
            "status": "error",
            "provider": PROVIDER,
            "tool_used": "air_quality",
            "error": classify_error(exc, "weather"),
            "data": "",
        }

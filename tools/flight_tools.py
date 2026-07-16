"""Kiwi MCP flight search tool."""

from __future__ import annotations

import asyncio
import traceback
from datetime import datetime
from typing import Any

from mcp import ClientSession, types
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client

from config.settings import settings
from utils.error_categories import classify_error

TOOL_NAME = "search-flight"
DEFAULT_TIMEOUT_SECONDS = 20
DEBUG = False


def _serialize_tool_result(result: Any) -> dict:
    """Convert MCP CallToolResult into a serializable dictionary."""
    structured = getattr(result, "structuredContent", None)
    payload: dict[str, Any] = {}

    if structured:
        payload["structured"] = structured

    content_entries = []
    for content in getattr(result, "content", []) or []:
        if isinstance(content, types.TextContent):
            content_entries.append({"type": "text", "text": content.text})
        elif isinstance(content, types.ImageContent):
            content_entries.append(
                {"type": "image", "mime_type": content.mimeType, "data": content.data}
            )
        elif isinstance(content, types.EmbeddedResource):
            resource = content.resource
            if isinstance(resource, types.TextResourceContents):
                content_entries.append(
                    {
                        "type": "resource",
                        "uri": resource.uri,
                        "text": resource.text,
                    }
                )
            else:
                content_entries.append(
                    {
                        "type": "resource",
                        "uri": resource.uri,
                        "data": resource.blob,
                    }
                )
        else:
            content_entries.append({"type": "unknown", "value": str(content)})

    if content_entries:
        payload["content"] = content_entries

    return payload


def _log_exception_details(exc: BaseException) -> str:
    """Print and return detailed exception diagnostics."""
    details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    print("MCP ERROR DETAILS")
    print(details)
    return details


async def _list_tools_and_call(
    url: str, payload: dict, timeout_seconds: int
) -> dict[str, Any]:
    """Connect to MCP server, list tools, and call the flight search tool."""
    def _get_tool_schema(tool: Any) -> dict[str, Any] | None:
        if isinstance(tool, dict):
            return tool.get("inputSchema")
        return getattr(tool, "inputSchema", None)

    def _get_tool_name(tool: Any) -> str | None:
        if isinstance(tool, dict):
            return tool.get("name")
        return getattr(tool, "name", None)

    def _prepare_payload(tool_schema: dict[str, Any] | None) -> dict[str, Any]:
        if not tool_schema:
            return payload

        schema_properties = tool_schema.get("properties") or {}
        adjusted = dict(payload)

        if schema_properties:
            adjusted = {key: value for key, value in adjusted.items() if key in schema_properties}

        required_fields = tool_schema.get("required") or []
        missing = [
            field
            for field in required_fields
            if field not in adjusted or adjusted.get(field) in (None, "")
        ]
        if missing:
            raise ValueError(
                f"Missing required inputs for '{TOOL_NAME}': {missing}. Payload: {adjusted}"
            )

        return adjusted

    normalized = url.rstrip("/")
    if normalized.endswith("/sse"):
        async with sse_client(url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await asyncio.wait_for(session.initialize(), timeout=timeout_seconds)
                tools = await asyncio.wait_for(
                    session.list_tools(), timeout=timeout_seconds
                )
                tool_names = [_get_tool_name(tool) for tool in tools.tools]
                if TOOL_NAME not in tool_names:
                    raise RuntimeError(
                        f"Tool '{TOOL_NAME}' not available. Tools: {tool_names}"
                    )
                tool = next(
                    tool for tool in tools.tools if _get_tool_name(tool) == TOOL_NAME
                )
                tool_schema = _get_tool_schema(tool)
                prepared_payload = _prepare_payload(tool_schema)
                if DEBUG:
                    print("TOOL SCHEMA:")
                    print(tool_schema)
                    print("FINAL PAYLOAD:")
                    print(prepared_payload)
                result = await asyncio.wait_for(
                    session.call_tool(TOOL_NAME, prepared_payload), timeout=timeout_seconds
                )
                return {"tools": tool_names, "result": result}

    async with streamable_http_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await asyncio.wait_for(session.initialize(), timeout=timeout_seconds)
            tools = await asyncio.wait_for(session.list_tools(), timeout=timeout_seconds)
            tool_names = [_get_tool_name(tool) for tool in tools.tools]
            if TOOL_NAME not in tool_names:
                raise RuntimeError(
                    f"Tool '{TOOL_NAME}' not available. Tools: {tool_names}"
                )
            tool = next(
                tool for tool in tools.tools if _get_tool_name(tool) == TOOL_NAME
            )
            tool_schema = _get_tool_schema(tool)
            prepared_payload = _prepare_payload(tool_schema)
            if DEBUG:
                print("TOOL SCHEMA:")
                print(tool_schema)
                print("FINAL PAYLOAD:")
                print(prepared_payload)
            result = await asyncio.wait_for(
                session.call_tool(TOOL_NAME, prepared_payload), timeout=timeout_seconds
            )
            return {"tools": tool_names, "result": result}


def _format_departure_date(event_date: str | None) -> str | None:
    """Convert YYYY-MM-DD to DD/MM/YYYY for the Kiwi MCP tool."""
    if not event_date:
        return None
    return datetime.strptime(event_date, "%Y-%m-%d").strftime("%d/%m/%Y")


async def search_flights(
    origin: str | None = None,
    destination: str | None = None,
    event_date: str | None = None,
    travelers: int = 1,
) -> dict:
    """Search flights using the Kiwi MCP tool."""
    departure_date = _format_departure_date(event_date)
    payload = {
        "flyFrom": origin,
        "flyTo": destination,
        "departureDate": departure_date,
        "adults": travelers,
    }

    try:
        response = await _list_tools_and_call(
            settings.kiwi_mcp_server_url, payload, DEFAULT_TIMEOUT_SECONDS
        )
        result = response["result"]
        if getattr(result, "isError", False):
            error_payload = _serialize_tool_result(result)
            error_details = f"Tool execution failed. Result: {error_payload}"
            return {
                "status": "error",
                "provider": "kiwi",
                "tool_used": TOOL_NAME,
                "error": error_details,
                "data": error_payload,
                "available_tools": response["tools"],
            }

        data = _serialize_tool_result(result)
        if "content" in data and isinstance(data["content"], list):
            data["content"] = data["content"][:5]
        return {
            "status": "success",
            "provider": "kiwi",
            "tool_used": TOOL_NAME,
            "data": data,
            "available_tools": response["tools"],
        }
    except asyncio.TimeoutError as exc:
        _log_exception_details(exc)
        return {
            "status": "error",
            "provider": "kiwi",
            "tool_used": TOOL_NAME,
            "error": classify_error(exc, "flight"),
            "data": {},
        }
    except Exception as exc:
        _log_exception_details(exc)
        return {
            "status": "error",
            "provider": "kiwi",
            "tool_used": TOOL_NAME,
            "error": classify_error(exc, "flight"),
            "data": {},
        }
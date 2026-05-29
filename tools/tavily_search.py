"""Tavily Search wrapper for destination research."""

from typing import Any

from config.settings import settings


def web_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Return deterministic dummy search results until Tavily is wired in."""
    return [
        {
            "title": "Dummy destination research",
            "url": "https://example.com/trip-planner-placeholder",
            "content": f"Placeholder Tavily result for: {query}",
            "score": 1.0,
            "provider": "tavily",
            "status": "dummy",
            "api_key_configured": bool(settings.tavily_api_key),
        }
        for _ in range(max(1, min(max_results, 3)))
    ]

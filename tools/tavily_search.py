"""Tavily web search tool wrapper."""

import asyncio
import logging
from typing import Any

from tavily import TavilyClient

from config.settings import settings
from utils.error_categories import classify_error

logger = logging.getLogger(__name__)

# Reuse one client instead of constructing per-call (see note below)
_client: TavilyClient | None = None


def _get_client() -> TavilyClient:
    global _client
    if _client is None:
        _client = TavilyClient(api_key=settings.tavily_api_key)
    return _client


def _sync_search(query: str, max_results: int) -> dict[str, Any]:
    """Blocking call — must only ever run inside run_in_executor, never awaited directly."""
    client = _get_client()
    response = client.search(query=query, max_results=max_results, timeout=15)
    return {"query": query, "results": response.get("results", [])}


async def search_web(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the web with Tavily and return structured results."""
    if not settings.tavily_api_key:
        logger.error("Tavily API key is not configured.")
        return {
            "query": query,
            "results": [],
            "error": "TAVILY_API_KEY is not configured.",
        }

    retries = 3
    loop = asyncio.get_running_loop()

    for attempt in range(1, retries + 1):
        try:
            logger.info("Running Tavily search. attempt=%s query=%s", attempt, query)
            return await loop.run_in_executor(None, _sync_search, query, max_results)
        except Exception as exc:
            logger.exception("Tavily search failed. attempt=%s query=%s", attempt, query)
            if attempt == retries:
                return {
                    "query": query,
                    "results": [],
                    "error": classify_error(exc, "search"),
                }
            await asyncio.sleep(attempt)
"""Tavily web search tool wrapper."""

import logging
import time
from typing import Any

from tavily import TavilyClient

from config.settings import settings

logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the web with Tavily and return structured results."""
    if not settings.tavily_api_key:
        logger.error("Tavily API key is not configured.")
        return {
            "query": query,
            "results": [],
            "error": "TAVILY_API_KEY is not configured.",
        }

    client = TavilyClient(api_key=settings.tavily_api_key)
    retries = 3

    for attempt in range(1, retries + 1):
        try:
            logger.info("Running Tavily search. attempt=%s query=%s", attempt, query)
            response = client.search(query=query, max_results=max_results, timeout=15)

            return {
                "query": query,
                "results": response.get("results", []),
            }
        except Exception as exc:
            logger.exception("Tavily search failed. attempt=%s query=%s", attempt, query)
            if attempt == retries:
                return {
                    "query": query,
                    "results": [],
                    "error": str(exc),
                }

            time.sleep(attempt)

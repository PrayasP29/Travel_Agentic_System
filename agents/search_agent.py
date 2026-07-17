"""Destination research agent powered by Tavily search."""

from langchain.agents import create_agent

from cache import cache_service
from cache.cache_keys import CacheKeys, SEARCH_TTL
from config.models import get_text_llm
from tools.tavily_search import search_web
from utils.error_categories import classify_error
from utils.helpers import last_message_content


async def search_agent(state: dict) -> dict:
    """Use a LangChain agent to decide whether web search is needed."""
    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    destination = updated_state.get("destination")
    venue = updated_state.get("venue")

    cache_key = CacheKeys.search(destination or "", venue or "")
    cached = await cache_service.get(cache_key)
    if cached is not None:
        updated_state.update(cached)
        updated_state["errors"] = errors
        return updated_state

    try:
        interests = updated_state.get("interests")
        trip_style = updated_state.get("trip_style")

        agent = create_agent(
            model=get_text_llm(),
            tools=[search_web],
            system_prompt=(
                "You are a destination research specialist. "
                "Your sole responsibility is destination research.\n\n"
                "Preserve every useful discovered attraction, restaurant, transportation, "
                "and local-tip detail. Remove duplicate entries only.\n\n"
                "DO NOT provide:\n"
                "- Itinerary planning or scheduling\n"
                "- Hotel or accommodation recommendations\n"
                "- Flight or airport guidance\n"
                "- Booking or reservation advice\n"
                "- Arrival, departure, or return-trip planning\n\n"
                "If your search results contain travel logistics, flights, or hotels, "
                "ignore that content entirely. Output only attractions, restaurants, "
                "local transit information, and local tips.\n\n"
                "Return markdown in exactly this structure:\n\n"
                "Venue Highlights\n\n"
                "Top Attractions\n\n"
                "* Attraction 1\n"
                "* Attraction 2\n"
                "* Attraction 3\n\n"
                "Recommended Restaurants\n\n"
                "* Restaurant 1\n"
                "* Restaurant 2\n"
                "* Restaurant 3\n\n"
                "Transportation Options\n\n"
                "* Option 1\n"
                "* Option 2\n"
                "* Option 3\n\n"
                "Local Tips\n\n"
                "* Tip 1\n"
                "* Tip 2\n"
                "* Tip 3\n\n"
                "CRITICAL: Perform exactly ONE search_web call. "
                "Formulate a single broad query covering attractions, restaurants, "
                "transportation, and local tips together. "
                "Do NOT do follow-up searches. Work with whatever the first search "
                "returns. If a category has few results, note it and move on."
            ),
        )

        prompt = (
            "Perform ONE search_web call with a broad query covering all research "
            "needs below. Do not search again regardless of results. "
            "Work with what the first search returns.\n\n"
            f"Destination: {destination}\n"
            f"Venue: {venue}\n"
            f"Interests: {interests}\n"
            f"Trip Style: {trip_style}\n\n"
            "Return a structured summary with Venue Highlights, Top Attractions, "
            "Recommended Restaurants, Transportation Options, and Local Tips. "
            "Keep all discovered useful information and remove duplicates only.\n\n"
            "Do not include flights, hotels, itinerary planning, booking advice, "
            "or any arrival/departure guidance."
        )

        response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
        )
        search_notes = last_message_content(response)

        updated_state["search_results"] = response
        updated_state["search_notes"] = (
            search_notes or "Search agent completed without additional notes."
        )
        updated_state["search_status"] = "completed"
        await cache_service.set(cache_key, {
            "search_notes": updated_state.get("search_notes"),
            "search_status": updated_state.get("search_status"),
        }, ttl=SEARCH_TTL)
    except Exception as exc:
        errors.append(classify_error(exc, "search"))
        updated_state["search_results"] = updated_state.get("search_results", {})
        updated_state["search_notes"] = classify_error(exc, "search")
        updated_state["search_status"] = "failed"

    updated_state["errors"] = errors
    return updated_state

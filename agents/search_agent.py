"""Destination research agent powered by Tavily search."""

from langchain.agents import create_agent

from config.models import get_text_llm
from tools.tavily_search import search_web


def _last_message_content(response: dict) -> str:
    """Extract the final message content from a LangChain agent response."""
    messages = response.get("messages", [])
    if not messages:
        return ""
    return getattr(messages[-1], "content", "") or ""


def search_agent(state: dict) -> dict:
    """Use a LangChain agent to decide whether web search is needed."""
    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    try:
        destination = updated_state.get("destination")
        venue = updated_state.get("venue")
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
                "* Tip 3"
            ),
        )

        prompt = (
            "Use search_web to research the following destination and venue.\n\n"
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

        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        search_notes = _last_message_content(response)

        updated_state["search_results"] = response
        updated_state["search_notes"] = (
            search_notes or "Search agent completed without additional notes."
        )
        updated_state["search_status"] = "completed"
    except Exception as exc:
        errors.append(f"search_agent failed: {exc}")
        updated_state["search_results"] = updated_state.get("search_results", {})
        updated_state["search_notes"] = "Web search failed."
        updated_state["search_status"] = "failed"

    updated_state["errors"] = errors
    return updated_state

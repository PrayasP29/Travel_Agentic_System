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
                "ONLY provide:\n"
                "- Top attractions at the destination\n"
                "- Recommended local restaurants\n"
                "- Local transportation advice (subway, taxi, walking, etc.)\n\n"
                "DO NOT provide:\n"
                "- Itinerary planning or scheduling\n"
                "- Hotel or accommodation recommendations\n"
                "- Flight or airport guidance\n"
                "- Booking or reservation advice\n"
                "- Arrival, departure, or return-trip planning\n\n"
                "If your search results contain travel logistics, flights, or hotels, "
                "ignore that content entirely. Output only attractions, restaurants, "
                "and local transit information."
            ),
        )

        prompt = (
            "Use search_web to research the following destination and venue.\n\n"
            f"Destination: {destination}\n"
            f"Venue: {venue}\n"
            f"Interests: {interests}\n"
            f"Trip Style: {trip_style}\n\n"
            "Return a concise, structured summary covering exactly three sections:\n"
            "1. Top Attractions — notable places to visit near the destination and venue\n"
            "2. Recommended Restaurants — highly-rated local dining options\n"
            "3. Local Transportation — practical transit tips for getting around\n\n"
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
"""Hotel agent for finding and summarizing hotel options."""

from langchain.agents import create_agent

from config.models import get_text_llm
from tools.hotel_tools import search_hotels


def _last_message_content(response: dict) -> str:
    """Extract the final message content from a LangChain agent response."""
    messages = response.get("messages", [])
    if not messages:
        return ""
    return getattr(messages[-1], "content", "") or ""


def hotel_agent(state: dict) -> dict:
    """Use a LangChain agent to decide whether hotel search is needed."""
    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    try:
        destination = updated_state.get("destination")
        venue = updated_state.get("venue")
        event_date = updated_state.get("event_date")
        travelers = updated_state.get("travelers", 1)
        budget = updated_state.get("budget")
        hotel_preferences = updated_state.get("hotel_preferences")

        agent = create_agent(
            model=get_text_llm(),
            tools=[search_hotels],
            system_prompt=(
                "You are a hotel planning agent. Determine hotel requirements, "
                "decide whether hotel search is needed, call the registered "
                "search_hotels tool when appropriate, interpret results, and "
                "provide concise hotel recommendations."
            ),
        )

        prompt = (
            "Review this hotel planning state. Decide whether the hotel search "
            "tool is needed. If needed, call search_hotels. Then summarize the "
            "hotel options, recommendations, and reasoning.\n\n"
            f"destination: {destination}\n"
            f"venue: {venue}\n"
            f"event_date: {event_date}\n"
            f"travelers: {travelers}\n"
            f"budget: {budget}\n"
            f"hotel_preferences: {hotel_preferences}"
        )

        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        hotel_notes = _last_message_content(response)

        updated_state["hotel_details"] = response
        updated_state["hotel_notes"] = (
            hotel_notes or "Hotel agent completed without additional notes."
        )
        updated_state["hotel_status"] = "completed"
    except Exception as exc:
        errors.append(f"hotel_agent failed: {exc}")
        updated_state["hotel_details"] = updated_state.get("hotel_details", {})
        updated_state["hotel_notes"] = "Hotel search failed."
        updated_state["hotel_status"] = "failed"

    updated_state["errors"] = errors
    return updated_state

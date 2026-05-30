"""Itinerary agent that turns gathered data into a draft trip plan."""

from langchain.agents import create_agent

from config.models import get_text_llm


def _last_message_content(response: dict) -> str:
    """Extract the final message content from a LangChain agent response."""
    messages = response.get("messages", [])
    if not messages:
        return ""
    return getattr(messages[-1], "content", "") or ""


def itinerary_agent(state: dict) -> dict:
    """Create a concise itinerary using flights, hotels, weather, and search output."""
    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    try:
        destination = updated_state.get("destination")
        venue = updated_state.get("venue")
        event_date = updated_state.get("event_date")

        agent = create_agent(
            model=get_text_llm(),
            tools=[],
            system_prompt=(
                "You are an itinerary planning agent. Combine all specialist agent "
                "outputs, create a complete travel itinerary, provide event-day "
                "recommendations, and return-trip recommendations. Be concise and "
                "actionable."
            ),
        )

        prompt = (
            "Use the provided state to draft a complete itinerary. "
            "Summarize flight, hotel, weather, and search insights. "
            "Include event-day recommendations and return-trip guidance.\n\n"
            f"destination: {destination}\n"
            f"venue: {venue}\n"
            f"event_date: {event_date}\n\n"
            f"flight_details: {updated_state.get('flight_details')}\n"
            f"hotel_details: {updated_state.get('hotel_details')}\n"
            f"weather_details: {updated_state.get('weather_details')}\n"
            f"search_results: {updated_state.get('search_results')}\n\n"
            f"flight_notes: {updated_state.get('flight_notes')}\n"
            f"hotel_notes: {updated_state.get('hotel_notes')}\n"
            f"weather_notes: {updated_state.get('weather_notes')}\n"
            f"search_notes: {updated_state.get('search_notes')}"
        )

        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        itinerary = _last_message_content(response)

        updated_state["itinerary"] = itinerary or "Itinerary agent completed without content."
        updated_state["itinerary_notes"] = (
            itinerary or "Itinerary agent completed without additional notes."
        )
        updated_state["itinerary_status"] = "completed"
    except Exception as exc:
        errors.append(f"itinerary_agent failed: {exc}")
        updated_state["itinerary"] = updated_state.get("itinerary", "")
        updated_state["itinerary_notes"] = "Itinerary generation failed."
        updated_state["itinerary_status"] = "failed"

    updated_state["errors"] = errors
    return updated_state

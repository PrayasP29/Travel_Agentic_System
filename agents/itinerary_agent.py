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
        supervisor_notes = updated_state.get("supervisor_notes")
        flight_notes = updated_state.get("flight_notes")
        hotel_notes = updated_state.get("hotel_notes")
        weather_notes = updated_state.get("weather_notes")
        search_notes = updated_state.get("search_notes")

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
            "Draft a complete itinerary using the concise notes provided. "
            "Include event-day recommendations and return-trip guidance.\n\n"
            f"Destination: {destination}\n"
            f"Venue: {venue}\n"
            f"Event Date: {event_date}\n\n"
            "Supervisor Notes:\n"
            f"{supervisor_notes}\n\n"
            "Flight Notes:\n"
            f"{flight_notes}\n\n"
            "Hotel Notes:\n"
            f"{hotel_notes}\n\n"
            "Weather Notes:\n"
            f"{weather_notes}\n\n"
            "Search Notes:\n"
            f"{search_notes}"
        )

        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        itinerary = _last_message_content(response)

        updated_state["itinerary"] = itinerary or "Itinerary agent completed without content."
        updated_state["itinerary_notes"] = (
            itinerary or "Itinerary agent completed without additional notes."
        )
        updated_state["itinerary_status"] = "completed"
        updated_state["status"] = "completed"
    except Exception as exc:
        errors.append(f"itinerary_agent failed: {exc}")
        updated_state["itinerary"] = updated_state.get("itinerary", "")
        updated_state["itinerary_notes"] = "Itinerary generation failed."
        updated_state["itinerary_status"] = "failed"
        updated_state["status"] = "failed"

    updated_state["errors"] = errors
    return updated_state

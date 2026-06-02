
"""Itinerary agent that turns gathered data into a draft trip plan."""

from langchain.agents import create_agent

from config.models import get_text_llm
from agents.report_formatter_agent import report_formatter_agent


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

        supervisor_notes = updated_state.get("supervisor_notes", "")
        flight_notes = updated_state.get("flight_notes", "")
        hotel_notes = updated_state.get("hotel_notes", "")
        weather_notes = updated_state.get("weather_notes", "")
        search_notes = updated_state.get("search_notes", "")

        agent = create_agent(
            model=get_text_llm(),
            tools=[],
            system_prompt=(
                "You are an itinerary planning agent. "
                "Create a complete travel itinerary using all available information. "
                "Include arrival recommendations, hotel check-in suggestions, "
                "event-day guidance, local highlights, dining recommendations, "
                "and return-trip planning. Keep the output concise and actionable."
            ),
        )

        prompt = (
            "Create a complete travel itinerary.\n\n"
            f"Destination: {destination}\n"
            f"Venue: {venue}\n"
            f"Event Date: {event_date}\n\n"
            f"Supervisor Notes:\n{supervisor_notes}\n\n"
            f"Flight Notes:\n{flight_notes}\n\n"
            f"Hotel Notes:\n{hotel_notes}\n\n"
            f"Weather Notes:\n{weather_notes}\n\n"
            f"Search Notes:\n{search_notes}\n"
        )

        response = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ]
            }
        )

        itinerary = _last_message_content(response)

        updated_state["itinerary"] = (
            itinerary
            or "Itinerary agent completed without content."
        )

        updated_state["itinerary_notes"] = (
            itinerary
            or "Itinerary agent completed without additional notes."
        )

        updated_state["itinerary_status"] = "completed"

        # Generate final formatted report
        report_res = report_formatter_agent(updated_state)
        if isinstance(report_res, dict):
            updated_state["final_report"] = report_res.get("final_report", "")
        else:
            updated_state["final_report"] = str(report_res)

        updated_state["status"] = "completed"

    except Exception as exc:
        errors.append(f"itinerary_agent failed: {exc}")

        updated_state["itinerary"] = updated_state.get(
            "itinerary",
            "",
        )

        updated_state["itinerary_notes"] = (
            "Itinerary generation failed."
        )

        updated_state["itinerary_status"] = "failed"
        updated_state["status"] = "failed"

    updated_state["errors"] = errors
    return updated_state

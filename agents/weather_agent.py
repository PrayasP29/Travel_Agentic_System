"""Weather agent for retrieving and summarizing forecast details."""

from langchain.agents import create_agent

from config.models import get_text_llm
from tools.weather_tools import get_weather


def _last_message_content(response: dict) -> str:
    """Extract the final message content from a LangChain agent response."""
    messages = response.get("messages", [])
    if not messages:
        return ""
    return getattr(messages[-1], "content", "") or ""


def weather_agent(state: dict) -> dict:
    """Use a LangChain agent to decide whether weather lookup is needed."""
    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    try:
        destination = updated_state.get("destination")
        event_date = updated_state.get("event_date")

        weather_result = get_weather(destination=destination, event_date=event_date)
        updated_state["weather_details"] = weather_result
        if weather_result.get("status") != "success":
            updated_state["weather_status"] = "failed"
            updated_state["weather_notes"] = (
                "Weather retrieval failed: "
                f"{weather_result.get('error', 'Unknown error')}"
            )
            updated_state["errors"] = errors
            return updated_state

        updated_state["weather_notes"] = "Weather data retrieved successfully."
        updated_state["weather_status"] = "completed"
        updated_state["errors"] = errors
        return updated_state
    except Exception as exc:
        errors.append(f"weather_agent failed: {exc}")
        updated_state["weather_details"] = updated_state.get("weather_details", {})
        updated_state["weather_notes"] = "Weather lookup failed."
        updated_state["weather_status"] = "failed"

    updated_state["errors"] = errors
    return updated_state

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

        agent = create_agent(
            model=get_text_llm(),
            tools=[get_weather],
            system_prompt=(
                "You are a weather planning agent. Decide whether weather lookup "
                "is necessary, call the registered get_weather tool when needed, "
                "analyze the forecast, and provide concise recommendations."
            ),
        )

        prompt = (
            "Review this trip-planning state. Decide whether the weather lookup "
            "tool is needed. If needed, call get_weather. Then summarize the "
            "forecast, recommendations, and reasoning.\n\n"
            f"destination: {destination}\n"
            f"event_date: {event_date}"
        )

        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        weather_notes = _last_message_content(response)

        updated_state["weather_details"] = response
        updated_state["weather_notes"] = (
            weather_notes or "Weather agent completed without additional notes."
        )
        updated_state["weather_status"] = "completed"
    except Exception as exc:
        errors.append(f"weather_agent failed: {exc}")
        updated_state["weather_details"] = updated_state.get("weather_details", {})
        updated_state["weather_notes"] = "Weather lookup failed."
        updated_state["weather_status"] = "failed"

    updated_state["errors"] = errors
    return updated_state

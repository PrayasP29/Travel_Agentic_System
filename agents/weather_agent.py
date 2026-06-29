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

        agent = create_agent(
            model=get_text_llm(),
            tools=[],
            system_prompt=(
                "You are a weather analyst agent for a travel planner. "
                "Analyze the forecast and air quality data and preserve every useful "
                "weather, climate, air quality, and travel-advice detail available in "
                "the provided data. Remove duplicate facts only.\n"
                "Return markdown in exactly this structure:\n\n"
                "Weather Forecast\n\n"
                "Forecast Summary\n\n"
                "* Conditions: ...\n"
                "* Temperature Range: ...\n"
                "* Rain Probability: ...\n\n"
                "Historical Expectations\n\n"
                "* Historical climate information: ...\n"
                "* Seasonal expectations: ...\n\n"
                "Air Quality\n\n"
                "* AQI: ...\n"
                "* PM2.5: ...\n"
                "* PM10: ...\n"
                "* Ozone: ...\n"
                "* NO2: ...\n"
                "* SO2: ...\n"
                "* CO: ...\n\n"
                "Travel Advice\n\n"
                "* Clothing recommendations: ...\n"
                "* Weather precautions: ...\n"
                "* Event day considerations: ...\n\n"
                "Use 'Not available' only for fields genuinely absent from the data. "
                "Keep all AQI pollutant values when present.\n"
                "If the event date is further in the future than the 16-day forecast range, "
                "note that the date is beyond the daily forecast range, summarize the current 16-day forecast "
                "as representative weather, and provide historical climate expectations for that destination in that month."
            ),
        )

        prompt = (
            "Summarize the weather forecast and air quality for the trip.\n\n"
            f"Destination: {destination}\n"
            f"Event Date: {event_date}\n\n"
            f"Weather Data:\n{weather_result}"
        )

        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        weather_notes = _last_message_content(response)

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

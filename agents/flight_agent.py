"""Flight agent for finding and summarizing flight options."""

from langchain.agents import create_agent

from config.models import get_text_llm
from tools.flight_tools import search_flights


def _last_message_content(response: dict) -> str:
    """Extract the final message content from a LangChain agent response."""
    messages = response.get("messages", [])
    if not messages:
        return ""
    return getattr(messages[-1], "content", "") or ""


def flight_agent(state: dict) -> dict:
    """Use a LangChain agent to decide whether flight search is needed."""
    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    try:
        destination = updated_state.get("destination")
        event_date = updated_state.get("event_date")
        origin = updated_state.get("origin")
        travelers = updated_state.get("travelers", 1)

        agent = create_agent(
            model=get_text_llm(),
            tools=[search_flights],
            system_prompt=(
                "You are a flight planning agent. Analyze travel requirements, "
                "decide whether flight search is necessary, call the registered "
                "search_flights tool when needed, interpret results, and produce "
                "concise recommendations. Keep future Kiwi MCP compatibility in mind."
            ),
        )

        prompt = (
            "Review this flight planning state. Decide whether the flight search "
            "tool is needed. If needed, call search_flights. Then summarize the "
            "available flights, recommendations, and reasoning.\n\n"
            f"destination: {destination}\n"
            f"event_date: {event_date}\n"
            f"origin: {origin}\n"
            f"travelers: {travelers}"
        )
        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        flight_notes = _last_message_content(response)

        updated_state["flight_details"] = response
        updated_state["flight_notes"] = (
            flight_notes or "Flight agent completed without additional notes."
        )
        updated_state["flight_status"] = "completed"
    except Exception as exc:
        errors.append(f"flight_agent failed: {exc}")
        updated_state["flight_details"] = updated_state.get("flight_details", {})
        updated_state["flight_notes"] = "Flight search failed."
        updated_state["flight_status"] = "failed"

    updated_state["errors"] = errors
    return updated_state

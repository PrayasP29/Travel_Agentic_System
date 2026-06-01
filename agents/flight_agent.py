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
    """Run deterministic flight search, then summarize results."""
    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    print("\n" + "=" * 80)
    print("FLIGHT AGENT RECEIVED STATE")
    print("=" * 80)
    print("origin =", updated_state.get("origin"))
    print("destination =", updated_state.get("destination"))
    print("event_date =", updated_state.get("event_date"))
    print("travelers =", updated_state.get("travelers"))
    print("\nFULL STATE:")
    print(updated_state)

    try:
        destination = updated_state.get("destination")
        event_date = updated_state.get("event_date")
        origin = updated_state.get("origin")
        travelers = updated_state.get("travelers", 1)

        print("\nSEARCH_FLIGHTS INPUTS")
        print("origin =", origin)
        print("destination =", destination)
        print("event_date =", event_date)
        print("travelers =", travelers)

        flight_result = search_flights(
            origin=origin,
            destination=destination,
            event_date=event_date,
            travelers=travelers,
        )
        updated_state["flight_details"] = flight_result
        if flight_result.get("status") != "success":
            updated_state["flight_notes"] = (
                "Flight search failed: "
                f"{flight_result.get('error', 'Unknown error')}"
            )
            updated_state["flight_status"] = "failed"
            updated_state["errors"] = errors
            return updated_state

        agent = create_agent(
            model=get_text_llm(),
            tools=[],
            system_prompt=(
                "You are a flight planning agent. Summarize the flight search "
                "results and provide concise recommendations."
            ),
        )

        prompt = (
            "Summarize the flight search results and provide recommendations.\n\n"
            f"origin: {origin}\n"
            f"destination: {destination}\n"
            f"event_date: {event_date}\n"
            f"travelers: {travelers}\n\n"
            f"flight_result: {flight_result}"
        )
        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        flight_notes = _last_message_content(response)

        updated_state["flight_notes"] = (
            flight_notes or "Flight agent completed without additional notes."
        )
        updated_state["flight_status"] = (
            "completed" if flight_result.get("status") == "success" else "failed"
        )
    except Exception as exc:
        errors.append(f"flight_agent failed: {exc}")
        updated_state["flight_details"] = updated_state.get("flight_details", {})
        updated_state["flight_notes"] = "Flight search failed."
        updated_state["flight_status"] = "failed"

    updated_state["errors"] = errors
    return updated_state

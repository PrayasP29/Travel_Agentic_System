"""Local discovery agent backed by the Agentorist MCP server."""

from langchain.agents import create_agent

from config.models import get_text_llm
from tools.hotel_tools import search_local_places


def _last_message_content(response: dict) -> str:
    """Extract the final message content from a LangChain agent response."""
    messages = response.get("messages", [])
    if not messages:
        return ""
    return getattr(messages[-1], "content", "") or ""


def local_agent(state: dict) -> dict:
    """Use a LangChain agent to decide whether local discovery is needed."""
    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    try:
        destination = updated_state.get("destination")
        venue = updated_state.get("venue")

        agent = create_agent(
            model=get_text_llm(),
            tools=[search_local_places],
            system_prompt=(
                "You are a local discovery agent. Decide whether local discovery "
                "search is needed, call the registered search_local_places tool "
                "when appropriate, analyze results, and recommend local spots."
            ),
        )

        prompt = (
            "Review this trip-planning state. Decide whether local discovery "
            "search is needed. If needed, call search_local_places. Then "
            "summarize recommendations and reasoning.\n\n"
            f"destination: {destination}\n"
            f"venue: {venue}"
        )

        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        local_notes = _last_message_content(response)

        updated_state["local_results"] = response
        updated_state["local_notes"] = (
            local_notes or "Local discovery agent completed without additional notes."
        )
        updated_state["local_status"] = "completed"
    except Exception as exc:
        errors.append(f"local_agent failed: {exc}")
        updated_state["local_results"] = updated_state.get("local_results", {})
        updated_state["local_notes"] = "Local discovery failed."
        updated_state["local_status"] = "failed"

    updated_state["errors"] = errors
    return updated_state

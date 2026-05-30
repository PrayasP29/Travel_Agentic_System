"""Destination research agent powered by Tavily search."""

from langchain.agents import create_agent

from config.models import get_text_llm
from tools.tavily_search import search_web


def _last_message_content(response: dict) -> str:
    """Extract the final message content from a LangChain agent response."""
    messages = response.get("messages", [])
    if not messages:
        return ""
    return getattr(messages[-1], "content", "") or ""


def search_agent(state: dict) -> dict:
    """Use a LangChain agent to decide whether web search is needed."""
    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    try:
        destination = updated_state.get("destination")
        venue = updated_state.get("venue")
        interests = updated_state.get("interests")
        trip_style = updated_state.get("trip_style")

        agent = create_agent(
            model=get_text_llm(),
            tools=[search_web],
            system_prompt=(
                "You are a destination research agent. Generate useful search "
                "queries, decide whether web search is needed, call the "
                "registered search_web tool when appropriate, analyze results, "
                "and recommend attractions and activities."
            ),
        )

        prompt = (
            "Review this trip-planning state. Decide whether the web search tool "
            "is needed. If needed, call search_web with a high-signal query. "
            "Then summarize attractions, activities, and recommendations.\n\n"
            f"destination: {destination}\n"
            f"venue: {venue}\n"
            f"interests: {interests}\n"
            f"trip_style: {trip_style}"
        )

        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        search_notes = _last_message_content(response)

        updated_state["search_results"] = response
        updated_state["search_notes"] = (
            search_notes or "Search agent completed without additional notes."
        )
        updated_state["search_status"] = "completed"
    except Exception as exc:
        errors.append(f"search_agent failed: {exc}")
        updated_state["search_results"] = updated_state.get("search_results", {})
        updated_state["search_notes"] = "Web search failed."
        updated_state["search_status"] = "failed"

    updated_state["errors"] = errors
    return updated_state

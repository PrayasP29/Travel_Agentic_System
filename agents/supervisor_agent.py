"""Supervisor agent for preparing trip-planner workflow state."""

from langchain.agents import create_agent

from config.models import get_text_llm


def supervisor_agent(state: dict) -> dict:
    """Validate and prepare state for downstream specialist agents."""
    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    if not updated_state.get("destination"):
        errors.append("destination is required.")

    if not updated_state.get("venue"):
        errors.append("venue is required.")

    if not updated_state.get("event_date"):
        errors.append("event_date is required.")

    updated_state.setdefault("flight_details", {})
    updated_state.setdefault("hotel_details", {})
    updated_state.setdefault("weather_details", {})
    updated_state.setdefault("search_results", {})
    updated_state.setdefault("itinerary", "")
    updated_state["errors"] = errors
    updated_state["status"] = "processing"

    llm = get_text_llm()
    agent = create_agent(
        model=llm,
        tools=[],
        system_prompt=(
            "You are a supervisor for a multi-agent trip planner. "
            "Review the current state, identify missing inputs, and summarize "
            "which specialist agents should run next. Do not call tools."
        ),
    )

    prompt = (
        "Review this trip-planning state and provide a concise supervisor "
        f"summary for downstream agents:\n\n{updated_state}"
    )

    try:
        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        messages = response.get("messages", [])
        updated_state["supervisor_notes"] = (
            messages[-1].content if messages else "Supervisor reviewed the state."
        )
    except Exception as exc:
        updated_state["supervisor_notes"] = "Supervisor fallback summary created."
        updated_state["errors"].append(f"supervisor summary failed: {exc}")

    return updated_state

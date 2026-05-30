"""Supervisor agent for orchestrating the trip-planner workflow."""

from langchain.agents import create_agent

from agents.flight_agent import flight_agent
from agents.hotel_agent import hotel_agent
from agents.itinerary_agent import itinerary_agent
from agents.search_agent import search_agent
from agents.weather_agent import weather_agent
from config.models import get_text_llm


def _last_message_content(response: dict) -> str:
    """Extract the final message content from a LangChain agent response."""
    messages = response.get("messages", [])
    if not messages:
        return ""
    return getattr(messages[-1], "content", "") or ""


def _build_execution_plan(state: dict) -> dict:
    """Build a structured execution plan based on existing agent outputs."""
    return {
        "run_flight_agent": not bool(state.get("flight_details")),
        "run_hotel_agent": not bool(state.get("hotel_details")),
        "run_weather_agent": not bool(state.get("weather_details")),
        "run_search_agent": not bool(state.get("search_results")),
    }


def supervisor_agent(state: dict) -> dict:
    """Orchestrate specialist agents and deliver the final trip plan."""
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
    updated_state.setdefault("flight_notes", "")
    updated_state.setdefault("hotel_notes", "")
    updated_state.setdefault("weather_notes", "")
    updated_state.setdefault("search_notes", "")
    updated_state.setdefault("itinerary_notes", "")
    updated_state["execution_plan"] = _build_execution_plan(updated_state)

    llm = get_text_llm()
    agent = create_agent(
        model=llm,
        tools=[],
        system_prompt=(
            "You are a supervisor for a multi-agent trip planner. "
            "Understand the travel request, review the current execution plan, "
            "and provide a concise supervisor summary that explains what will "
            "happen next."
        ),
    )

    prompt = (
        "Analyze the trip request and current state. Explain why the execution "
        "plan makes sense and call out any missing details.\n\n"
        f"Execution plan:\n{updated_state['execution_plan']}\n\n"
        f"State:\n{updated_state}"
    )

    try:
        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        updated_state["supervisor_notes"] = _last_message_content(response)
    except Exception as exc:
        errors.append(f"supervisor planning failed: {exc}")
        updated_state["supervisor_notes"] = "Supervisor fallback plan created."

    updated_state["errors"] = errors
    if errors:
        updated_state["status"] = "blocked"
        return updated_state

    execution_plan = updated_state.get("execution_plan", {})
    if execution_plan.get("run_flight_agent"):
        updated_state = flight_agent(updated_state)
    if execution_plan.get("run_hotel_agent"):
        updated_state = hotel_agent(updated_state)
    if execution_plan.get("run_weather_agent"):
        updated_state = weather_agent(updated_state)
    if execution_plan.get("run_search_agent"):
        updated_state = search_agent(updated_state)

    updated_state = itinerary_agent(updated_state)
    updated_state["status"] = (
        "completed" if updated_state.get("itinerary_status") == "completed" else "failed"
    )

    return updated_state

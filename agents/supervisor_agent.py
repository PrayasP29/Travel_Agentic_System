"""Supervisor agent for orchestrating the trip-planner workflow."""

from langchain.agents import create_agent

from config.models import get_text_llm

DEBUG = False

# Keys removed from the previous schema — excluded from LLM context
_DEPRECATED_STATE_KEYS = {
    "recommended_hotel_price",
    "hotel_price",
    "hotel_price_details_numeric",
}


def _last_message_content(response: dict) -> str:
    """Extract the final message content from a LangChain agent response."""
    messages = response.get("messages", [])
    if not messages:
        return ""
    return getattr(messages[-1], "content", "") or ""


def _build_execution_plan(state: dict) -> dict:
    """Build a structured execution plan based on existing agent outputs."""
    return {
        "run_flight_agent":  not bool(state.get("flight_details")),
        "run_hotel_agent":   not bool(state.get("hotel_details")),
        "run_weather_agent": not bool(state.get("weather_details")),
        "run_search_agent":  not bool(state.get("search_results")),
    }


def _build_hotel_summary(state: dict) -> str:
    """Build a clean hotel summary from current schema fields only."""
    hotel_price_details = state.get("hotel_price_details") or []
    hotel_booking_links = state.get("hotel_booking_links") or []
    hotel_notes         = state.get("hotel_notes", "")

    if not hotel_price_details and not hotel_notes:
        return "No hotel data available yet."

    lines = []

    if hotel_price_details:
        lines.append("Hotel Recommendations:")
        for h in hotel_price_details:
            name     = h.get("hotel", "Unknown")
            rating   = h.get("rating", "N/A")
            category = h.get("price_category") or "Not available"
            lines.append(f"  - {name}: Rating {rating}, Price Category: {category}")

    if hotel_booking_links:
        lines.append("Booking Links:")
        for link in hotel_booking_links:
            lines.append(f"  - {link}")

    if hotel_notes:
        lines.append(f"Hotel Notes: {hotel_notes}")

    return "\n".join(lines)


def _sanitize_state_for_llm(state: dict) -> dict:
    """Remove deprecated keys before passing state to the LLM."""
    return {k: v for k, v in state.items() if k not in _DEPRECATED_STATE_KEYS}


def supervisor_agent(state: dict) -> dict:
    """Orchestrate specialist agents and deliver the final trip plan."""
    if DEBUG:
        print("\n" + "=" * 80)
        print("SUPERVISOR RECEIVED STATE")
        print("=" * 80)
        print(state)

    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    validation_errors: list[str] = []
    if not updated_state.get("destination"):
        validation_errors.append("destination is required.")
    if not updated_state.get("venue"):
        validation_errors.append("venue is required.")
    if not updated_state.get("event_date"):
        validation_errors.append("event_date is required.")
    errors.extend(validation_errors)

    updated_state.setdefault("flight_details",  {})
    updated_state.setdefault("hotel_details",   {})
    updated_state.setdefault("weather_details", {})
    updated_state.setdefault("search_results",  {})
    updated_state.setdefault("itinerary",       "")
    updated_state.setdefault("flight_notes",    "")
    updated_state.setdefault("hotel_notes",     "")
    updated_state.setdefault("weather_notes",   "")
    updated_state.setdefault("search_notes",    "")
    updated_state.setdefault("itinerary_notes", "")
    updated_state["execution_plan"] = _build_execution_plan(updated_state)

    llm   = get_text_llm()
    agent = create_agent(
        model=llm,
        tools=[],
        system_prompt=(
            "You are a supervisor for a multi-agent trip planner. "
            "Understand the travel request, review the current execution plan, "
            "and provide a concise supervisor summary that explains what will happen next.\n\n"
            "When summarizing hotel information:\n"
            "- Use hotel name, rating, and price category (e.g. $$).\n"
            "- Never mention numeric hotel prices such as 0.0 or $241/night.\n"
            "- Never reference recommended_hotel_price.\n"
            "- Use price categories exactly as provided (e.g. $, $$, $$$, $$$$)."
        ),
    )

    hotel_summary   = _build_hotel_summary(updated_state)
    sanitized_state = _sanitize_state_for_llm(updated_state)

    prompt = (
        "Analyze the trip request and current state. Explain why the execution "
        "plan makes sense and call out any missing details.\n\n"
        f"Execution Plan:\n{updated_state['execution_plan']}\n\n"
        f"Hotel Summary:\n{hotel_summary}\n\n"
        f"Full State:\n{sanitized_state}"
    )

    try:
        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        updated_state["supervisor_notes"] = _last_message_content(response)
    except Exception as exc:
        errors.append(f"supervisor planning failed: {exc}")
        updated_state["supervisor_notes"] = "Supervisor fallback plan created."
        updated_state["status"]           = "degraded"

    updated_state["errors"] = errors
    if validation_errors:
        updated_state["status"] = "blocked"
        if DEBUG:
            print("\nSUPERVISOR RETURNING STATE")
            print(updated_state)
        return updated_state

    if DEBUG:
        print("\nSUPERVISOR RETURNING STATE")
        print(updated_state)
    return updated_state

"""Itinerary agent that turns gathered data into a draft trip plan."""

import time
from langchain.agents import create_agent

from cache import cache_service
from cache.cache_keys import CacheKeys, ITINERARY_TTL
from config.models import get_text_llm
from agents.report_formatter_agent import report_formatter_agent


def _last_message_content(response: dict) -> str:
    """Extract the final message content from a LangChain agent response."""
    if response is None:
        return ""

    if isinstance(response, str):
        return response

    if isinstance(response, dict):
        messages = response.get("messages", [])
    else:
        messages = getattr(response, "messages", None)
        if messages is None and hasattr(response, "content"):
            return getattr(response, "content", "") or ""
        if messages is None:
            return str(response)

    if not messages:
        return ""

    last_message = messages[-1]
    if isinstance(last_message, dict):
        return last_message.get("content", "") or ""

    return getattr(last_message, "content", "") or str(last_message)


def _build_fallback_itinerary(state: dict) -> str:
    """Create a non-empty itinerary from already collected agent outputs."""
    origin = state.get("origin", "Unknown")
    destination = state.get("destination", "Unknown")
    venue = state.get("venue", "Not specified")
    event_date = state.get("event_date", "Unknown")
    flight_notes = state.get("flight_notes", "No flight information available.")
    hotel_notes = state.get("hotel_notes", "No hotel information available.")
    weather_notes = state.get("weather_notes", "No weather information available.")
    search_notes = state.get("search_notes", "No destination information available.")

    return f"""\
Fallback Itinerary

Trip Overview:
- Origin: {origin}
- Destination: {destination}
- Venue: {venue}
- Event Date: {event_date}

Flight Plan:
{flight_notes}

Hotel Plan:
{hotel_notes}

Weather Considerations:
{weather_notes}

Local Planning Notes:
{search_notes}
"""


async def itinerary_agent(state: dict) -> dict:
    """Create a concise itinerary using flights, hotels, weather, and search output."""
    _timer_start = time.time()
    print(f"[TIMER] itinerary_agent START: {_timer_start:.2f}")
    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    destination = updated_state.get("destination")
    venue = updated_state.get("venue")
    event_date = updated_state.get("event_date")

    cache_key = CacheKeys.itinerary(destination or "", venue or "", event_date or "")
    cached = await cache_service.get(cache_key)
    if cached is not None:
        updated_state.update(cached)
        updated_state["errors"] = errors
        print(f"[TIMER] itinerary_agent END: {time.time():.2f} (elapsed: {time.time() - _timer_start:.1f}s) [CACHE HIT]")
        return updated_state

    try:
        print("[DIAG-ITIN] try block entered")
        supervisor_notes = updated_state.get("supervisor_notes", "")
        flight_notes = updated_state.get("flight_notes", "")
        hotel_notes = updated_state.get("hotel_notes", "")
        weather_notes = updated_state.get("weather_notes", "")
        search_notes = updated_state.get("search_notes", "")

        agent = create_agent(
            model=get_text_llm(),
            tools=[],
            system_prompt=(
                "You are an itinerary planning agent. "
                "Create a complete travel itinerary using all available information. "
                "Include arrival recommendations, hotel check-in suggestions, "
                "event-day guidance, local highlights, dining recommendations, "
                "and return-trip planning. Keep the output concise and actionable."
            ),
        )

        prompt = (
            "Create a complete travel itinerary.\n\n"
            f"Destination: {destination}\n"
            f"Venue: {venue}\n"
            f"Event Date: {event_date}\n\n"
            f"Supervisor Notes:\n{supervisor_notes}\n\n"
            f"Flight Notes:\n{flight_notes}\n\n"
            f"Hotel Notes:\n{hotel_notes}\n\n"
            f"Weather Notes:\n{weather_notes}\n\n"
            f"Search Notes:\n{search_notes}\n"
        )

        print("[DIAG-ITIN] calling agent.invoke() (sync)...")
        response = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ]
            }
        )
        print(f"[DIAG-ITIN] agent.invoke() returned type={type(response).__name__}")

        itinerary = _last_message_content(response)

        updated_state["itinerary"] = (
            itinerary
            or "Itinerary agent completed without content."
        )

        updated_state["itinerary_notes"] = (
            itinerary
            or "Itinerary agent completed without additional notes."
        )

        updated_state["itinerary_status"] = "completed"

        # Generate final formatted report
        report_res = report_formatter_agent(updated_state)
        if isinstance(report_res, dict):
            updated_state["final_report"] = report_res.get("final_report", "")
        else:
            updated_state["final_report"] = str(report_res)

        updated_state["status"] = "completed"

        print(f"[DIAG-ITIN] calling cache_service.set(key={cache_key})")
        set_result = await cache_service.set(cache_key, {
            "itinerary": updated_state.get("itinerary"),
            "itinerary_notes": updated_state.get("itinerary_notes"),
            "itinerary_status": updated_state.get("itinerary_status"),
            "final_report": updated_state.get("final_report"),
            "status": updated_state.get("status"),
        }, ttl=ITINERARY_TTL)
        print(f"[DIAG-ITIN] cache_service.set returned: {set_result}")

    except Exception as exc:
        import traceback
        print(f"[DIAG-ITIN] EXCEPT triggered: {type(exc).__name__}: {exc}")
        print(f"[DIAG-ITIN] traceback:\n{traceback.format_exc()}")
        errors.append(f"itinerary_agent failed: {exc}")
        errors.append("itinerary generation fallback was used.")

        fallback_itinerary = _build_fallback_itinerary(updated_state)
        updated_state["itinerary"] = fallback_itinerary

        updated_state["itinerary_notes"] = fallback_itinerary

        updated_state["itinerary_status"] = "failed"

        report_res = report_formatter_agent(updated_state)
        if isinstance(report_res, dict):
            updated_state["final_report"] = (
                report_res.get("final_report")
                or "Final report generation completed without content."
            )
        else:
            updated_state["final_report"] = (
                str(report_res)
                or "Final report generation completed without content."
            )

        updated_state["status"] = "failed"

    updated_state["errors"] = errors
    print(f"[TIMER] itinerary_agent END: {time.time():.2f} (elapsed: {time.time() - _timer_start:.1f}s)")
    return updated_state

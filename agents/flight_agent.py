"""Flight agent for finding and summarizing flight options."""

import json
import re

from langchain.agents import create_agent

from config.models import get_text_llm
from tools.flight_tools import search_flights

DEBUG = False


def parse_flight_data(flight_result: dict) -> list:
    """Parse raw flight results and return a list of flight details."""
    try:
        if flight_result.get("status") != "success":
            return []
        data = flight_result.get("data", {})
        content_list = data.get("content", [])
        for content in content_list:
            if content.get("type") == "text":
                text = content.get("text", "")
                if text.strip().startswith("["):
                    return json.loads(text)
    except Exception:
        pass
    return []


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

    if DEBUG:
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
        event_date  = updated_state.get("event_date")
        origin      = updated_state.get("origin")
        travelers   = updated_state.get("travelers", 1)

        if DEBUG:
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

        flights_list = parse_flight_data(flight_result)
        flights_summary_for_agent = ""
        if flights_list:
            for idx, f in enumerate(flights_list, 1):
                departure_local = f.get("departure", {}).get("local", "")
                arrival_local   = f.get("arrival", {}).get("local", "")
                price           = f.get("price")
                currency        = f.get("currency", "EUR")
                layovers        = f.get("layovers", [])
                layover_str     = (
                    f"with layovers in {', '.join(l.get('city', '') for l in layovers)}"
                    if layovers else "direct"
                )
                flights_summary_for_agent += (
                    f"Flight {idx}:\n"
                    f"  - Route: {f.get('flyFrom')} -> {f.get('flyTo')} ({f.get('cityFrom')} -> {f.get('cityTo')})\n"
                    f"  - Departure: {departure_local}\n"
                    f"  - Arrival: {arrival_local}\n"
                    f"  - Price: {price} {currency}\n"
                    f"  - Details: {layover_str}\n"
                    f"  - Link: {f.get('deepLink')}\n\n"
                )
        else:
            flights_summary_for_agent = "No flights returned in flight_result."

        # Extract default booking link and price from flights_list
        booking_link = ""
        flight_price = 0.0
        if flights_list:
            first_flight = flights_list[0]
            booking_link = (
                first_flight.get("deepLink")
                or first_flight.get("booking_url")
                or first_flight.get("url")
                or first_flight.get("bookingLink")
                or first_flight.get("share_url")
                or ""
            )
            price_val = first_flight.get("price")
            if price_val is not None:
                try:
                    flight_price = float(price_val)
                except (ValueError, TypeError):
                    pass

        agent = create_agent(
            model=get_text_llm(),
            tools=[],
            system_prompt=(
                "You are a flight planning agent. Your task is to review the list of available flights, "
                "select the best option for the traveler (e.g. considering price, duration, direct vs layovers), "
                "and generate a concise recommendation summary.\n"
                "Your output summary MUST contain exactly these fields in markdown:\n"
                "Recommended Flight\n\n"
                "Route:\n"
                "[Departure City/Airport] → [Arrival City/Airport]\n\n"
                "Departure:\n"
                "[Departure Time]\n\n"
                "Arrival:\n"
                "[Arrival Time]\n\n"
                "Price:\n"
                "[Price with currency]\n\n"
                "Booking Link:\n"
                "[Booking Link URL]\n\n"
                "Provide this summary in clear markdown format. Do not output raw JSON."
            ),
        )

        prompt = (
            "Select the best flight from the list below and summarize it.\n\n"
            f"origin: {origin}\n"
            f"destination: {destination}\n"
            f"event_date: {event_date}\n"
            f"travelers: {travelers}\n\n"
            f"Available Flights:\n{flights_summary_for_agent}"
        )
        response     = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        flight_notes = _last_message_content(response)

        # Post-process response to extract actual selected flight's booking link and price
        selected_booking_link = booking_link
        urls = re.findall(r'https?://[^\s\)\*]+', flight_notes)
        if urls:
            selected_booking_link = urls[0]

        selected_price = flight_price
        price_matches  = re.findall(r'Price:\s*(\d+(?:\.\d+)?)', flight_notes, re.IGNORECASE)
        if not price_matches:
            price_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:EUR|USD)', flight_notes, re.IGNORECASE)
        if price_matches:
            try:
                selected_price = float(price_matches[0])
            except ValueError:
                pass

        updated_state["flight_booking_link"]      = selected_booking_link
        updated_state["recommended_flight_price"] = selected_price
        updated_state["flight_notes"]             = (
            flight_notes or "Flight agent completed without additional notes."
        )
        updated_state["flight_status"] = (
            "completed" if flight_result.get("status") == "success" else "failed"
        )
    except Exception as exc:
        errors.append(f"flight_agent failed: {exc}")
        updated_state["flight_details"] = updated_state.get("flight_details", {})
        updated_state["flight_notes"]   = "Flight search failed."
        updated_state["flight_status"]  = "failed"

    updated_state["errors"] = errors
    return updated_state
"""Flight agent for finding and summarizing flight options."""

import json
import re
import time

from langchain.agents import create_agent

from cache import cache_service
from cache.cache_keys import CacheKeys, FLIGHT_TTL
from config.models import get_text_llm
from tools.flight_tools import search_flights

DEBUG = False


def _normalize_flight(it: dict) -> dict:
    """Normalize new Kiwi nested structure to flat format if needed."""
    if "outbound" in it:
        out = it["outbound"]
        norm = dict(it)
        norm["flyFrom"] = out.get("from", it.get("flyFrom", "Unknown"))
        norm["flyTo"] = out.get("to", it.get("flyTo", "Unknown"))
        norm["cityFrom"] = out.get("from", it.get("cityFrom", ""))
        norm["cityTo"] = out.get("to", it.get("cityTo", ""))
        norm["departure"] = {"local": out.get("departureTime", "")}
        norm["arrival"] = {"local": out.get("arrivalTime", "")}
        if "bookingUrl" in it and not norm.get("deepLink"):
            norm["deepLink"] = it["bookingUrl"]
        segments = out.get("segments", [])
        if segments:
            norm["segments"] = segments
            if len(segments) > 1:
                norm["layovers"] = [
                    {"city": s.get("to", ""), "airport": s.get("to", "")}
                    for i, s in enumerate(segments[:-1])
                ]
        return norm
    return it


def parse_flight_data(flight_result: dict) -> list:
    """Parse raw flight results and return a list of flight details."""
    try:
        if flight_result.get("status") != "success":
            return []
        data = flight_result.get("data", {})

        structured = data.get("structured")
        if structured:
            itineraries = structured.get("itineraries")
            if itineraries:
                return [_normalize_flight(it) for it in itineraries]

        content_list = data.get("content", [])
        for content in content_list:
            if content.get("type") == "text":
                text = content.get("text", "").strip()
                if text:
                    parsed = json.loads(text)
                    if isinstance(parsed, list):
                        return [_normalize_flight(it) for it in parsed]
                    if isinstance(parsed, dict):
                        itineraries = parsed.get("itineraries")
                        if itineraries:
                            return [_normalize_flight(it) for it in itineraries]
    except Exception:
        pass
    return []


def _last_message_content(response: dict) -> str:
    """Extract the final message content from a LangChain agent response."""
    messages = response.get("messages", [])
    if not messages:
        return ""
    return getattr(messages[-1], "content", "") or ""


def _format_flight_notes(flights_list: list, fallback_notes: str) -> str:
    """Format all returned flight records without dropping MCP fields."""
    if not flights_list:
        return fallback_notes or "No flights returned in flight_result."

    sections = ["Flight Information"]
    seen = set()

    for idx, flight in enumerate(flights_list, 1):
        identity = (
            flight.get("flyFrom"),
            flight.get("flyTo"),
            flight.get("departure", {}).get("local"),
            flight.get("arrival", {}).get("local"),
            flight.get("price"),
            flight.get("deepLink"),
        )
        if identity in seen:
            continue
        seen.add(identity)

        departure = flight.get("departure", {}) or {}
        arrival = flight.get("arrival", {}) or {}
        layovers = flight.get("layovers", []) or []
        currency = flight.get("currency", "EUR")
        booking_link = (
            flight.get("deepLink")
            or flight.get("booking_url")
            or flight.get("url")
            or flight.get("bookingLink")
            or flight.get("share_url")
            or "Not available"
        )
        duration = (
            flight.get("duration")
            or flight.get("durationText")
            or flight.get("duration_text")
            or flight.get("fly_duration")
            or "Not available"
        )
        price = flight.get("price")
        price_text = f"{price} {currency}" if price is not None else "Not available"
        route = (
            f"{flight.get('flyFrom', 'Unknown')} → {flight.get('flyTo', 'Unknown')}"
        )
        city_route = (
            f"{flight.get('cityFrom', '')} → {flight.get('cityTo', '')}".strip(" →")
        )
        layover_notes = (
            "Direct flight"
            if not layovers
            else "Layovers: "
            + ", ".join(
                filter(
                    None,
                    [
                        layover.get("city")
                        or layover.get("airport")
                        or layover.get("flyTo")
                        for layover in layovers
                    ],
                )
            )
        )

        additional_notes = [layover_notes]
        if city_route:
            additional_notes.append(f"City route: {city_route}")

        sections.append(
            f"\nFlight {idx}\n\n"
            "Route:\n"
            f"{route}\n\n"
            "Departure Time:\n"
            f"{departure.get('local') or departure.get('utc') or 'Not available'}\n\n"
            "Arrival Time:\n"
            f"{arrival.get('local') or arrival.get('utc') or 'Not available'}\n\n"
            "Duration:\n"
            f"{duration}\n\n"
            "Price:\n"
            f"{price_text}\n\n"
            "Booking Link:\n"
            f"{booking_link}\n\n"
            "Additional Notes:\n"
            + "\n".join(f"- {note}" for note in additional_notes if note)
        )

    if fallback_notes:
        sections.append(f"\nAgent Recommendation Notes:\n{fallback_notes}")

    return "\n".join(sections)


async def flight_agent(state: dict) -> dict:
    """Run deterministic flight search, then summarize results."""
    _timer_start = time.time()
    print(f"[TIMER] flight_agent START: {_timer_start:.2f}")
    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    destination = updated_state.get("destination")
    event_date  = updated_state.get("event_date")
    origin      = updated_state.get("origin")
    travelers   = updated_state.get("travelers", 1)

    cache_key = CacheKeys.flight(origin or "", destination or "", event_date or "", str(travelers))
    cached = await cache_service.get(cache_key)
    if cached is not None:
        updated_state.update(cached)
        updated_state["errors"] = errors
        print(f"[TIMER] flight_agent END: {time.time():.2f} (elapsed: {time.time() - _timer_start:.1f}s) [CACHE HIT]")
        return updated_state

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
        if DEBUG:
            print("\nSEARCH_FLIGHTS INPUTS")
            print("origin =", origin)
            print("destination =", destination)
            print("event_date =", event_date)
            print("travelers =", travelers)

        flight_result = await search_flights(
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
            print(f"[TIMER] flight_agent END: {time.time():.2f} (elapsed: {time.time() - _timer_start:.1f}s)")
            return updated_state

        flights_list = parse_flight_data(flight_result)
        flights_list = flights_list[:5]
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
        response     = await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})
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
            _format_flight_notes(
                flights_list,
                flight_notes or "Flight agent completed without additional notes.",
            )
        )
        updated_state["flight_status"] = (
            "completed" if flight_result.get("status") == "success" else "failed"
        )
        if updated_state["flight_status"] == "completed":
            await cache_service.set(cache_key, {
                "flight_details": updated_state.get("flight_details"),
                "flight_booking_link": updated_state.get("flight_booking_link"),
                "recommended_flight_price": updated_state.get("recommended_flight_price"),
                "flight_notes": updated_state.get("flight_notes"),
                "flight_status": updated_state.get("flight_status"),
            }, ttl=FLIGHT_TTL)
    except Exception as exc:
        errors.append(f"flight_agent failed: {exc}")
        updated_state["flight_details"] = updated_state.get("flight_details", {})
        updated_state["flight_notes"]   = "Flight search failed."
        updated_state["flight_status"]  = "failed"

    updated_state["errors"] = errors
    print(f"[TIMER] flight_agent END: {time.time():.2f} (elapsed: {time.time() - _timer_start:.1f}s)")
    return updated_state

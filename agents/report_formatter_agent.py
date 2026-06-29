"""Final report formatter for trip planner output — deterministic string assembly."""

from __future__ import annotations

import re


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _clean_text(value: object, fallback: str) -> str:
    """Return text with duplicate non‑empty lines removed, preserving order."""
    if value is None:
        return fallback

    text = str(value).strip()
    if not text:
        return fallback

    lines = []
    seen = set()
    for line in text.splitlines():
        normalized = line.strip()
        if normalized and normalized in seen:
            continue
        if normalized:
            seen.add(normalized)
        lines.append(line)

    cleaned = "\n".join(lines).strip()
    return cleaned or fallback


def _extract_between_headings(
    text: str, start_terms: list[str], stop_terms: list[str]
) -> str:
    """Extract an existing notes subsection by heading text."""
    lines = text.splitlines()
    start_index = None

    for index, line in enumerate(lines):
        heading = line.strip().strip("#").strip().lower()
        if any(term in heading for term in start_terms):
            start_index = index + 1
            break

    if start_index is None:
        return ""

    end_index = len(lines)
    for index in range(start_index, len(lines)):
        heading = lines[index].strip().strip("#").strip().lower()
        if heading and any(term in heading for term in stop_terms):
            end_index = index
            break

    return "\n".join(lines[start_index:end_index]).strip()


def _dedent(text: str) -> str:
    """Remove common leading whitespace from every line."""
    lines = text.splitlines()
    stripped = [l.lstrip() for l in lines]
    return "\n".join(stripped)


# ═══════════════════════════════════════════════════════════════════════════════
# Section: Executive Summary
# ═══════════════════════════════════════════════════════════════════════════════


def _format_executive_summary(state: dict) -> str:
    origin = state.get("origin", "Unknown")
    destination = state.get("destination", "Unknown")
    event_date = state.get("event_date", "Unknown")
    venue = state.get("venue", "Not specified")

    return f"""\
## Executive Summary

This report provides a comprehensive overview for your trip.

* **Origin:** {origin}
* **Destination:** {destination}
* **Event Date:** {event_date}
* **Venue:** {venue}

Below you will find flight options, hotel recommendations, weather forecasts,
local attractions, and a suggested day‑wise itinerary to help plan your
journey.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Section: Trip Overview
# ═══════════════════════════════════════════════════════════════════════════════


def _format_trip_overview(state: dict) -> str:
    origin = state.get("origin", "Unknown")
    destination = state.get("destination", "Unknown")
    event_date = state.get("event_date", "Unknown")
    venue = state.get("venue", "Not specified")

    lines = [
        "## Trip Overview",
        "",
        f"| Detail | Value |",
        f"|--------|-------|",
        f"| **Origin** | {origin} |",
        f"| **Destination** | {destination} |",
        f"| **Venue** | {venue} |",
        f"| **Event Date** | {event_date} |",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Section: Flights
# ═══════════════════════════════════════════════════════════════════════════════


def _parse_flight_notes(flight_notes: str) -> tuple[list[str], str]:
    """Split flight_notes into a list of individual flight blocks and a
    recommendation string.

    The flight_notes text has the shape::

        Flight Information

        Flight 1\n\nRoute:\n…

        Flight 2\n\nRoute:\n…

        Agent Recommendation Notes:\n…
    """
    if not flight_notes:
        return [], ""

    # Separate the "Agent Recommendation Notes:" trailer
    rec_match = re.search(
        r"\nAgent Recommendation Notes:\s*(.*)", flight_notes, re.DOTALL
    )
    rec_text = rec_match.group(1).strip() if rec_match else ""
    body = flight_notes[: rec_match.start()] if rec_match else flight_notes

    # Split remaining body at "\nFlight N\n" boundaries
    flights = re.split(r"\n(?=Flight \d+\n)", body)

    # First block is the header ("Flight Information") — discard it
    flight_blocks = []
    for block in flights:
        stripped = block.strip()
        if stripped and not re.match(r"^Flight Information$", stripped, re.IGNORECASE):
            flight_blocks.append(stripped)

    return flight_blocks, rec_text


def _format_flight_block(flight_text: str, index: int = 0) -> str:
    """Convert a raw flight block into a uniform sub‑section."""
    prefix = "⭐ " if index == 0 else ""
    lines = [f"### {prefix}Flight {index + 1}", ""]
    for line in flight_text.splitlines():
        # Skip the "Flight N" header itself (already in the heading)
        if re.match(r"^Flight \d+$", line.strip()):
            continue
        if re.match(r"^Flight Information", line.strip(), re.IGNORECASE):
            continue
        # Convert "Route:\nMIA → EWR" into "**Route:** MIA → EWR"
        field_match = re.match(
            r"^(Route|Departure Time|Arrival Time|Duration|Price|Booking Link"
            r"|Additional Notes):\s*$",
            line.strip(),
            re.IGNORECASE,
        )
        if field_match:
            lines.append("")
            lines.append(f"**{field_match.group(1)}:**")
            continue
        lines.append(line)

    return "\n".join(lines)


def _format_flights(state: dict) -> tuple[str, str]:
    """Return (recommended_flight_section, other_flights_section)."""
    flight_notes = _clean_text(state.get("flight_notes"), "")
    if not flight_notes:
        return "", ""

    flights, rec_text = _parse_flight_notes(flight_notes)
    if not flights:
        return "", ""

    # --- recommended flight (first) ---
    rec_lines = ["## ⭐ Recommended Flight", ""]
    rec_lines.append(_format_flight_block(flights[0], 0))
    if rec_text:
        rec_lines.append("")
        rec_lines.append("### Agent's Recommendation")
        rec_lines.append("")
        rec_lines.append(rec_text)
    recommended = "\n".join(rec_lines)

    # --- other flights ---
    other = ""
    if len(flights) > 1:
        other_lines = ["## Other Available Flights", ""]
        for i, f in enumerate(flights[1:], 1):
            other_lines.append(_format_flight_block(f, i))
            other_lines.append("")
            other_lines.append("---")
            other_lines.append("")
        # Remove trailing separator
        while other_lines and other_lines[-1] in ("", "---"):
            other_lines.pop()
        other = "\n".join(other_lines)

    return recommended, other


# ═══════════════════════════════════════════════════════════════════════════════
# Section: Hotels
# ═══════════════════════════════════════════════════════════════════════════════


def _parse_hotel_notes(hotel_notes: str) -> tuple[list[str], str]:
    """Split hotel_notes into a list of individual hotel blocks and an
    additional notes string.

    The hotel_notes text has the shape::

        Hotel Recommendations

        Hotel 1\n\n* Name: …\n* Rating: …\n…

        Hotel 2\n\n* Name: …\n* Rating: …\n…

        Additional Recommendation Notes:\n…
    """
    if not hotel_notes:
        return [], ""

    # Separate the "Additional Recommendation Notes:" trailer
    add_match = re.search(
        r"\nAdditional Recommendation Notes:\s*(.*)", hotel_notes, re.DOTALL
    )
    add_text = add_match.group(1).strip() if add_match else ""
    body = hotel_notes[: add_match.start()] if add_match else hotel_notes

    # Split remaining body at "\nHotel N\n" boundaries
    hotels = re.split(r"\n(?=Hotel \d+\n)", body)

    hotel_blocks = []
    for block in hotels:
        stripped = block.strip()
        if stripped and not re.match(
            r"^Hotel Recommendations$", stripped, re.IGNORECASE
        ):
            hotel_blocks.append(stripped)

    return hotel_blocks, add_text


def _format_hotel_block(hotel_text: str, index: int = 0) -> str:
    """Convert a raw hotel block into a clean sub‑section."""
    prefix = "⭐ " if index == 0 else ""
    lines = [f"### {prefix}Hotel {index + 1}", ""]
    for line in hotel_text.splitlines():
        if re.match(r"^Hotel \d+$", line.strip()):
            continue
        if re.match(r"^Hotel Recommendations$", line.strip(), re.IGNORECASE):
            continue
        lines.append(line)
    return "\n".join(lines)


def _format_hotels(state: dict) -> tuple[str, str]:
    """Return (recommended_hotels_section, additional_hotels_section)."""
    hotel_notes = _clean_text(state.get("hotel_notes"), "")
    if not hotel_notes:
        return "", ""

    hotels, add_text = _parse_hotel_notes(hotel_notes)
    if not hotels:
        return "", ""

    # --- recommended hotel (first) ---
    rec_lines = ["## ⭐ Recommended Hotels", ""]
    rec_lines.append(_format_hotel_block(hotels[0], 0))
    if add_text:
        rec_lines.append("")
        rec_lines.append("### Additional Notes")
        rec_lines.append("")
        rec_lines.append(add_text)
    recommended = "\n".join(rec_lines)

    # --- additional hotels ---
    additional = ""
    if len(hotels) > 1:
        add_lines = ["## Additional Hotel Options", ""]
        for i, h in enumerate(hotels[1:], 1):
            add_lines.append(_format_hotel_block(h, i))
            add_lines.append("")
            add_lines.append("---")
            add_lines.append("")
        while add_lines and add_lines[-1] in ("", "---"):
            add_lines.pop()
        additional = "\n".join(add_lines)

    return recommended, additional


# ═══════════════════════════════════════════════════════════════════════════════
# Section: Weather
# ═══════════════════════════════════════════════════════════════════════════════


def _format_weather(state: dict) -> tuple[str, str]:
    """Return (weather_summary, weather_details)."""
    weather_notes = _clean_text(state.get("weather_notes"), "")
    if not weather_notes:
        return "", ""

    forecast = _extract_between_headings(
        weather_notes,
        ["forecast summary", "forecast"],
        ["historical expectations", "air quality", "travel advice"],
    )
    historical = _extract_between_headings(
        weather_notes,
        ["historical expectations"],
        ["air quality", "travel advice"],
    )
    air_quality = _extract_between_headings(
        weather_notes,
        ["air quality"],
        ["travel advice"],
    )
    travel_advice = _extract_between_headings(
        weather_notes,
        ["travel advice"],
        [],
    )

    # If the LLM didn't use the expected headings, show everything as summary
    if not any([forecast, historical, air_quality, travel_advice]):
        summary = weather_notes
        details = ""
        return summary, details

    summary_lines = ["## Weather Summary", ""]
    summary_lines.append(forecast or "Not available.")
    summary = "\n".join(summary_lines)

    details_lines = ["## Weather Details", ""]
    details_lines.append("### Historical Expectations")
    details_lines.append("")
    details_lines.append(historical or "Not available.")
    details_lines.append("")
    details_lines.append("---")
    details_lines.append("")
    details_lines.append("### Air Quality")
    details_lines.append("")
    details_lines.append(air_quality or "Not available.")
    if travel_advice:
        details_lines.append("")
        details_lines.append("---")
        details_lines.append("")
        details_lines.append("### Travel Advice")
        details_lines.append("")
        details_lines.append(travel_advice)
    details = "\n".join(details_lines)

    return summary, details


# ═══════════════════════════════════════════════════════════════════════════════
# Section: Local
# ═══════════════════════════════════════════════════════════════════════════════


def _format_local(state: dict) -> tuple[str, str, str]:
    """Return (highlights, restaurants, transportation)."""
    search_notes = _clean_text(state.get("search_notes"), "")
    if not search_notes:
        return "", "", ""

    attractions = _extract_between_headings(
        search_notes,
        ["top attractions", "attractions"],
        ["recommended restaurants", "restaurants", "transportation options", "local tips"],
    )
    restaurants = _extract_between_headings(
        search_notes,
        ["recommended restaurants", "restaurants"],
        ["transportation options", "transportation", "local tips"],
    )
    transportation = _extract_between_headings(
        search_notes,
        ["transportation options", "transportation"],
        ["local tips"],
    )
    local_tips = _extract_between_headings(
        search_notes,
        ["local tips"],
        [],
    )

    # If no headings matched, show everything as highlights
    if not any([attractions, restaurants, transportation]):
        attractions = search_notes

    highlights_lines = ["## Local Highlights", ""]
    highlights_lines.append(attractions or "Not available.")
    highlights = "\n".join(highlights_lines)

    rest_lines = ["## Restaurants", ""]
    rest_lines.append(restaurants or "Not available.")
    if local_tips:
        rest_lines.append("")
        rest_lines.append("---")
        rest_lines.append("")
        rest_lines.append("### Local Tips")
        rest_lines.append("")
        rest_lines.append(local_tips)
    restaurants_section = "\n".join(rest_lines)

    trans_lines = ["## Transportation", ""]
    trans_lines.append(transportation or "Not available.")
    transportation_section = "\n".join(trans_lines)

    return highlights, restaurants_section, transportation_section


# ═══════════════════════════════════════════════════════════════════════════════
# Section: Itinerary
# ═══════════════════════════════════════════════════════════════════════════════


def _format_itinerary(state: dict) -> str:
    itinerary = state.get("itinerary", "")
    if not itinerary or itinerary == "No itinerary available.":
        return "## Day-wise Itinerary\n\nNo itinerary available."

    lines = [
        "## Day-wise Itinerary",
        "",
        itinerary,
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Section: Booking Links
# ═══════════════════════════════════════════════════════════════════════════════


def _collect_booking_links(state: dict) -> list[str]:
    """Collect all booking links from the state for a consolidated list."""
    links = []
    seen = set()

    # Flight booking link from state
    flink = state.get("flight_booking_link")
    if flink and flink not in seen:
        links.append(f"* **Flight Booking:** {flink}")
        seen.add(flink)

    # Hotel booking links from state
    for hlink in (state.get("hotel_booking_links") or []):
        if hlink and hlink not in seen:
            links.append(f"* **Hotel Booking:** {hlink}")
            seen.add(hlink)

    # Also scrape from flight_notes for any additional links
    flight_notes = state.get("flight_notes", "") or ""
    for m in re.finditer(r"Booking Link:\s*(\S+)", flight_notes):
        url = m.group(1)
        if url != "Not available" and url not in seen:
            links.append(f"* **Flight Booking:** {url}")
            seen.add(url)

    return links


def _format_booking_links(state: dict) -> str:
    links = _collect_booking_links(state)
    if not links:
        return ""
    return "## Quick Links\n\n" + "\n".join(links)


# ═══════════════════════════════════════════════════════════════════════════════
# Section: Next Steps
# ═══════════════════════════════════════════════════════════════════════════════


def _format_action_items() -> str:
    return """\
## Next Steps

* [ ] Book flight
* [ ] Book hotel
* [ ] Review weather forecast
* [ ] Plan local transportation
* [ ] Pack appropriate clothing
* [ ] Confirm event tickets and venue details"""


# ═══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════════════════════════


# fmt: off
_SECTION_ORDER = [
    "exec_summary",       # Executive Summary
    "trip_overview",      # Trip Overview
    "rec_flight",         # Recommended Flight
    "other_flights",      # Other Available Flights
    "rec_hotels",         # Recommended Hotels
    "add_hotels",         # Additional Hotel Options
    "weather_summary",    # Weather Summary
    "weather_details",    # Weather Details
    "highlights",         # Local Highlights
    "restaurants",        # Restaurants
    "transportation",     # Transportation
    "itinerary",          # Day-wise Itinerary
    "quick_links",        # Quick Links (booking links consolidated)
    "next_steps",         # Next Steps
]
# fmt: on


def report_formatter_agent(state: dict) -> dict:
    """Assemble a structured, easy‑to‑read travel report from agent state.

    No LLM is used. Content from specialist agents is preserved verbatim.
    """
    rec_flight, other_flights = _format_flights(state)
    rec_hotels, add_hotels = _format_hotels(state)
    weather_summary, weather_details = _format_weather(state)
    highlights, restaurants, transportation = _format_local(state)

    sections_pool: dict[str, str] = {
        "exec_summary": _format_executive_summary(state),
        "trip_overview": _format_trip_overview(state),
        "rec_flight": rec_flight,
        "other_flights": other_flights,
        "rec_hotels": rec_hotels,
        "add_hotels": add_hotels,
        "weather_summary": weather_summary,
        "weather_details": weather_details,
        "highlights": highlights,
        "restaurants": restaurants,
        "transportation": transportation,
        "itinerary": _format_itinerary(state),
        "quick_links": _format_booking_links(state),
        "next_steps": _format_action_items(),
    }

    header = "# Executive Travel Report\n"

    parts = [header]
    for key in _SECTION_ORDER:
        text = sections_pool.get(key, "")
        if text.strip():
            parts.append(text)

    final_report = "\n\n---\n\n".join(parts)
    return {"final_report": final_report}

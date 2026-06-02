"""Final report formatter for trip planner output — deterministic string assembly."""

from __future__ import annotations


def report_formatter_agent(state: dict) -> dict:
    """Assemble a structured travel report directly from agent state.

    No LLM is used. Content from specialist agents is preserved verbatim.
    """
    origin        = state.get("origin",        "Unknown")
    destination   = state.get("destination",   "Unknown")
    event_date    = state.get("event_date",     "Unknown")
    venue         = state.get("venue",          "Not specified")
    flight_notes  = state.get("flight_notes",  "No flight information available.")
    hotel_notes   = state.get("hotel_notes",   "No hotel information available.")
    weather_notes = state.get("weather_notes", "No weather information available.")
    search_notes  = state.get("search_notes",  "No destination information available.")
    itinerary     = state.get("itinerary",     "No itinerary available.")

    # Optional booking links — only rendered when present.
    flight_booking_link = state.get("flight_booking_link", "")
    hotel_booking_links = state.get("hotel_booking_links", [])

    flights_section = flight_notes
    if flight_booking_link:
        flights_section += f"\n\n**Book here:** {flight_booking_link}"

    hotels_section = hotel_notes
    if hotel_booking_links:
        links = "\n".join(f"- {link}" for link in hotel_booking_links)
        hotels_section += f"\n\n**Booking Links:**\n{links}"

    final_report = f"""\
# Here's where things stand right now

## Trip Summary
- **Route:** {origin} → {destination}
- **Venue:** {venue}
- **Event Date:** {event_date}

## Flights
{flights_section}

## Hotels
{hotels_section}

## Weather
{weather_notes}

## Local Highlights
{search_notes}

## Suggested Itinerary
{itinerary}

## Next Steps
- Confirm and book your flight
- Confirm and book your hotel
- Review the weather forecast closer to the event date
- Follow the suggested itinerary on arrival
"""

    return {"final_report": final_report}
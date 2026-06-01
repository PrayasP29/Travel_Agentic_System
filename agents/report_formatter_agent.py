"""Final report formatter for trip planner output — LLM-powered."""

from core.llm import get_text_llm
from core.agent_factory import create_agent


def report_formatter_agent(state: dict) -> dict:
    """Generate a polished, LLM-powered final travel report."""

    origin        = state.get("origin", "Unknown")
    destination   = state.get("destination", "Unknown")
    event_date    = state.get("event_date", "Unknown")
    venue         = state.get("venue", "Not specified")
    flight_notes  = state.get("flight_notes",  "No flight information available.")
    hotel_notes   = state.get("hotel_notes",   "No hotel information available.")
    weather_notes = state.get("weather_notes", "No weather information available.")
    search_notes  = state.get("search_notes",  "No destination information available.")
    itinerary     = state.get("itinerary",     "No itinerary available.")

    system_prompt = """You are a professional travel consultant.
Create a polished travel briefing.
Format exactly:

# Here's where things stand right now

## Trip Summary
## Flights
## Hotels
## Weather
## Local Highlights
## Event Information
## Suggested Itinerary
## Next Steps

Rules:
- Use markdown headings.
- Use bullet points.
- Never output JSON.
- Never output raw state.
- Never repeat debug information.
- Summarize information professionally.
- Keep the report concise and readable.
- If information is missing, say "Information unavailable"."""

    user_prompt = f"""Please generate a professional travel report using the following trip details:

Origin: {origin}
Destination: {destination}
Event Venue: {venue}
Event Date: {event_date}

Flight Notes:
{flight_notes}

Hotel Notes:
{hotel_notes}

Weather Notes:
{weather_notes}

Destination / Search Notes:
{search_notes}

Suggested Itinerary:
{itinerary}

Return only the formatted travel report. Do not include any JSON, raw data, or debug output."""

    llm   = get_text_llm()
    agent = create_agent(llm=llm, system_prompt=system_prompt)

    response    = agent.invoke({"messages": [{"role": "user", "content": user_prompt}]})
    final_report = response["messages"][-1].content

    return {"final_report": final_report}
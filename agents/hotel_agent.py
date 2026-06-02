"""Hotel agent for summarizing hotel search results."""

from langchain.agents import create_agent

from config.models import get_text_llm
from tools.hotel_tools import search_hotels


def _last_message_content(response: dict) -> str:
    """Extract the final message content from a LangChain agent response."""
    messages = response.get("messages", [])
    if not messages:
        return ""
    return getattr(messages[-1], "content", "") or ""


def _format_price(place: dict) -> str:
    """Return the exact MCP price category. Never estimates or converts."""
    price_category = place.get("price")
    if price_category:
        return f"Price Category: {price_category}"
    return "Price Category: Not available"


def hotel_agent(state: dict) -> dict:
    """Use a LangChain agent to recommend hotels grounded in MCP data only."""
    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    try:
        destination       = updated_state.get("destination")
        venue             = updated_state.get("venue")
        event_date        = updated_state.get("event_date")
        travelers         = updated_state.get("travelers", 1)
        budget            = updated_state.get("budget")
        hotel_preferences = updated_state.get("hotel_preferences")

        hotel_result = search_hotels(destination=destination)
        updated_state["hotel_details"] = hotel_result

        if hotel_result.get("status") != "success":
            updated_state["hotel_status"] = "failed"
            updated_state["hotel_notes"] = (
                "Hotel search failed: "
                f"{hotel_result.get('error', 'Unknown error')}"
            )
            updated_state["errors"] = errors
            return updated_state

        # Extract real fields directly from MCP results — no estimation
        results             = hotel_result.get("data", {}).get("results", [])
        hotel_booking_links = []
        hotel_price_details = []
        mcp_hotel_summaries = []

        for place in results:
            b_url = (
                place.get("booking_url")
                or place.get("yelp_url")
                or place.get("url")
                or place.get("link")
            )
            if b_url:
                hotel_booking_links.append(b_url)

            name           = place.get("name", "Unknown Hotel")
            rating         = place.get("rating", "N/A")
            price_category = place.get("price")
            address        = place.get("address") or place.get("location") or ""

            # Store structured MCP price data — no numeric conversion
            hotel_price_details.append({
                "hotel":          name,
                "price_category": price_category,
                "rating":         rating,
            })

            price_line   = f"  - {_format_price(place)}"
            address_line = f"\n  - Address: {address}" if address else ""
            link_line    = f"\n  - Book: {b_url}" if b_url else ""

            mcp_hotel_summaries.append(
                f"- **{name}**\n"
                f"  - Rating: {rating}\n"
                f"{price_line}"
                f"{address_line}"
                f"{link_line}"
            )

        mcp_summary_block = (
            "\n".join(mcp_hotel_summaries)
            if mcp_hotel_summaries
            else "No hotel records returned by the data source."
        )

        agent = create_agent(
            model=get_text_llm(),
            tools=[],
            system_prompt=(
                "You are a hotel recommendation agent.\n\n"
                "Only use information that exists in the provided MCP data.\n\n"
                "Do not invent hotel prices.\n"
                "Do not invent booking URLs.\n"
                "Do not invent hotel availability.\n"
                "Do not convert price categories into nightly rates.\n"
                "Do not estimate hotel pricing.\n\n"
                "For pricing, use the exact price category returned by MCP "
                "(e.g. $, $$, $$$, $$$$).\n"
                "Display it exactly as: Price Category: $$\n"
                "Never output a nightly rate such as $241/night unless that "
                "exact value is present in the MCP data.\n\n"
                "Recommend hotels based on:\n"
                "- reputation\n"
                "- location\n"
                "- venue proximity\n"
                "- traveler preferences\n\n"
                "Use the MCP Hotel Results block as your only source of "
                "pricing, ratings, addresses, and URLs."
            ),
        )

        prompt = (
            "Summarize the hotel options below into a clean recommendation.\n"
            "Use the exact price categories, ratings, addresses, and booking "
            "links from the MCP results.\n"
            "Never convert price categories into nightly rates.\n\n"
            f"Destination: {destination}\n"
            f"Venue: {venue}\n"
            f"Event Date: {event_date}\n"
            f"Travelers: {travelers}\n"
            f"Budget: {budget}\n"
            f"Hotel Preferences: {hotel_preferences}\n\n"
            f"MCP Hotel Results:\n{mcp_summary_block}"
        )

        response    = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        hotel_notes = _last_message_content(response)

        updated_state["hotel_booking_links"] = hotel_booking_links
        updated_state["hotel_price_details"] = hotel_price_details
        updated_state["hotel_notes"]         = (
            hotel_notes or "Hotel search completed without additional notes."
        )
        updated_state["hotel_status"] = "completed"

    except Exception as exc:
        errors.append(f"hotel_agent failed: {exc}")
        updated_state["hotel_details"] = updated_state.get("hotel_details", {})
        updated_state["hotel_notes"]   = "Hotel search failed."
        updated_state["hotel_status"]  = "failed"

    updated_state["errors"] = errors
    return updated_state
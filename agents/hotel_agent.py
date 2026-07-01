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


def _format_hotel_notes(results: list, agent_notes: str) -> str:
    """Format hotel results with links attached to each matching hotel."""
    sections = ["Hotel Recommendations"]
    seen = set()
    hotel_number = 1

    for place in results:
        name = place.get("name", "Unknown Hotel")
        address = place.get("address") or place.get("location") or "Not available"
        identity = (name, address)
        if identity in seen:
            continue
        seen.add(identity)

        rating = place.get("rating", "N/A")
        price_category = place.get("price") or "Not available"
        booking_link = (
            place.get("booking_url")
            or place.get("yelp_url")
            or place.get("url")
            or place.get("link")
            or "Not available"
        )
        notes = []
        if place.get("description"):
            notes.append(str(place.get("description")))
        if place.get("categories"):
            notes.append(f"Categories: {place.get('categories')}")
        if place.get("phone"):
            notes.append(f"Phone: {place.get('phone')}")
        if place.get("review_count"):
            notes.append(f"Review Count: {place.get('review_count')}")
        if place.get("distance"):
            notes.append(f"Distance: {place.get('distance')}")
        if not notes:
            notes.append("Recommended based on MCP hotel search data.")

        sections.append(
            f"\nHotel {hotel_number}\n\n"
            f"* Name: {name}\n"
            f"* Rating: {rating}\n"
            f"* Address: {address}\n"
            f"* Price Category: {price_category}\n"
            f"* Booking Link: {booking_link}\n"
            f"* Recommendation Notes: {' '.join(notes)}"
        )
        hotel_number += 1

    if hotel_number == 1:
        sections.append("\nNo hotel records returned by the data source.")

    if agent_notes:
        sections.append(f"\nAdditional Recommendation Notes:\n{agent_notes}")

    return "\n".join(sections)


async def hotel_agent(state: dict) -> dict:
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

        hotel_result = await search_hotels(destination=destination)
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

        response    = await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})
        hotel_notes = _last_message_content(response)

        updated_state["hotel_booking_links"] = hotel_booking_links
        updated_state["hotel_price_details"] = hotel_price_details
        updated_state["hotel_notes"]         = (
            _format_hotel_notes(
                results,
                hotel_notes or "Hotel search completed without additional notes.",
            )
        )
        updated_state["hotel_status"] = "completed"

    except Exception as exc:
        errors.append(f"hotel_agent failed: {exc}")
        updated_state["hotel_details"] = updated_state.get("hotel_details", {})
        updated_state["hotel_notes"]   = "Hotel search failed."
        updated_state["hotel_status"]  = "failed"

    updated_state["errors"] = errors
    return updated_state

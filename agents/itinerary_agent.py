"""Itinerary agent that turns gathered data into a draft trip plan."""

from langchain_core.messages import HumanMessage

from config.models import get_text_llm
from tools.tavily_search import web_search


def itinerary_agent(state: dict) -> dict:
    """Create a concise itinerary using flights, hotels, weather, and web results."""
    llm = get_text_llm()
    destination = state.get("destination")
    web_context = state.get("search_results") or web_search(
        f"best things to do in {destination} travel itinerary"
    )

    prompt = (
        "Create a practical day-by-day trip itinerary. "
        "Use available flight, hotel, weather, and web-search context. "
        "Keep the output concise and hackathon-demo friendly."
    )
    response = llm.invoke([HumanMessage(content=f"{prompt}\n\nState: {state}\n\nWeb: {web_context}")])
    return {"itinerary": response.content}

"""Coordinator agent for routing trip-planning work through LangGraph."""

from langchain_core.messages import HumanMessage

from config.models import get_text_llm


def coordinator_agent(state: dict) -> dict:
    """Read the request and decide which specialist agents should help."""
    llm = get_text_llm()
    prompt = (
        "You are the coordinator for a multi-agent trip planner. "
        "Summarize the user's travel request and identify required steps."
    )
    response = llm.invoke([HumanMessage(content=f"{prompt}\n\nState: {state}")])
    return {"coordinator_notes": response.content}

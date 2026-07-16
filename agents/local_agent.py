"""Local discovery agent backed by the Agentorist MCP server."""

import time
from langchain.agents import create_agent

from config.models import get_text_llm
from tools.hotel_tools import search_local_places
from utils.error_categories import classify_error


def _last_message_content(response: dict) -> str:
    """Extract the final message content from a LangChain agent response."""
    messages = response.get("messages", [])
    if not messages:
        return ""
    return getattr(messages[-1], "content", "") or ""


async def local_agent(state: dict) -> dict:
    """Use a LangChain agent to decide whether local discovery is needed."""
    _t0 = time.perf_counter()
    print(f"[PHASE] local_agent ENTER: t={_t0:.3f}")

    _t1 = time.perf_counter()
    updated_state = dict(state)
    print(f"[PHASE] local_agent state_prep: t={_t1:.3f} +{( _t1 - _t0)*1000:.1f}ms")
    errors = list(updated_state.get("errors") or [])

    try:
        destination = updated_state.get("destination")
        venue = updated_state.get("venue")

        _t2 = time.perf_counter()
        agent = create_agent(
            model=get_text_llm(),
            tools=[search_local_places],
            system_prompt=(
                "You are a local discovery agent. Decide whether local discovery "
                "search is needed, call the registered search_local_places tool "
                "when appropriate, analyze results, and recommend local spots."
            ),
        )
        _t3 = time.perf_counter()
        print(f"[PHASE] local_agent create_agent: t={_t3:.3f} +{(_t3-_t2)*1000:.1f}ms")

        prompt = (
            "Review this trip-planning state. Decide whether local discovery "
            "search is needed. If needed, call search_local_places. Then "
            "summarize recommendations and reasoning.\n\n"
            f"destination: {destination}\n"
            f"venue: {venue}"
        )
        _t4 = time.perf_counter()
        print(f"[PHASE] local_agent prompt_built: t={_t4:.3f} +{(_t4-_t3)*1000:.1f}ms")

        _t5 = time.perf_counter()
        response = await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})
        _t6 = time.perf_counter()
        print(f"[PHASE] local_agent ainvoke_done: t={_t6:.3f} +{_t6-_t5:.3f}s (ainvoke total)")

        _t7 = time.perf_counter()
        local_notes = _last_message_content(response)
        print(f"[PHASE] local_agent parse_result: t={_t7:.3f} +{(_t7-_t6)*1000:.1f}ms")

        updated_state["local_results"] = response
        updated_state["local_notes"] = (
            local_notes or "Local discovery agent completed without additional notes."
        )
        updated_state["local_status"] = "completed"
        _t8 = time.perf_counter()
        print(f"[PHASE] local_agent state_update: t={_t8:.3f} +{(_t8-_t7)*1000:.1f}ms")
    except Exception as exc:
        errors.append(classify_error(exc, "local"))
        updated_state["local_results"] = updated_state.get("local_results", {})
        updated_state["local_notes"] = classify_error(exc, "local")
        updated_state["local_status"] = "failed"
        print(f"[PHASE] local_agent EXCEPTION: {exc}")

    updated_state["errors"] = errors
    _t9 = time.perf_counter()
    print(f"[PHASE] local_agent RETURN: t={_t9:.3f} +{_t9-_t0:.3f}s TOTAL")
    return updated_state

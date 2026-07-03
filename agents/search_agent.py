"""Destination research agent powered by Tavily search."""

import time

from langchain.agents import create_agent
from langchain_core.callbacks import BaseCallbackHandler

from config.models import get_text_llm
from tools.tavily_search import search_web


class _SearchTraceHandler(BaseCallbackHandler):
    """Callback handler to trace LLM and tool calls in search_agent."""

    def __init__(self):
        self.llm_calls = []
        self.tool_calls = []
        self._llm_start_ts = None
        self._llm_idx = 0
        self._tool_start_ts = None
        self._tool_name = None
        self._tool_query = None
        self._tool_idx = 0
        self.chain_log = []

    def on_llm_start(self, serialized, prompts, **kwargs):
        self._llm_idx += 1
        self._llm_start_ts = time.time()
        self.chain_log.append(f"LLM #{self._llm_idx}")
        print(f"\nLLM #{self._llm_idx}")
        print(f"  Started:  {self._llm_start_ts:.3f}")

    def on_llm_end(self, response, **kwargs):
        t = time.time()
        if self._llm_start_ts is None:
            return
        elapsed = t - self._llm_start_ts
        self.llm_calls.append({
            "idx": self._llm_idx, "start": self._llm_start_ts, "end": t, "elapsed": elapsed,
        })
        print(f"  Ended:    {t:.3f}")
        print(f"  Elapsed:  {elapsed:.3f}s")
        self._llm_start_ts = None

    def on_llm_error(self, error, **kwargs):
        t = time.time()
        if self._llm_start_ts:
            elapsed = t - self._llm_start_ts
            self.llm_calls.append({
                "idx": self._llm_idx, "start": self._llm_start_ts,
                "end": t, "elapsed": elapsed, "error": str(error)[:100],
            })
            print(f"  Error:    {str(error)[:100]}")
            print(f"  Elapsed:  {elapsed:.3f}s")
            self._llm_start_ts = None

    def on_tool_start(self, serialized, input_str, **kwargs):
        self._tool_idx += 1
        self._tool_start_ts = time.time()
        self._tool_name = serialized.get("name", "unknown")
        self._tool_query = input_str[:200]
        self.chain_log.append(f"Search #{self._tool_idx}")
        print(f"\nSearch #{self._tool_idx}")
        print(f"  Query:    {self._tool_query}")
        print(f"  Started:  {self._tool_start_ts:.3f}")

    def on_tool_end(self, output, **kwargs):
        t = time.time()
        if self._tool_start_ts is None:
            return
        elapsed = t - self._tool_start_ts
        self.tool_calls.append({
            "idx": self._tool_idx, "name": self._tool_name,
            "query": self._tool_query,
            "start": self._tool_start_ts, "end": t, "elapsed": elapsed,
        })
        print(f"  Ended:    {t:.3f}")
        print(f"  Elapsed:  {elapsed:.3f}s")
        returned_preview = str(output)[:150]
        print(f"  Returned: {returned_preview}")
        self._tool_start_ts = None

    def on_tool_error(self, error, **kwargs):
        t = time.time()
        if self._tool_start_ts:
            elapsed = t - self._tool_start_ts
            self.tool_calls.append({
                "idx": self._tool_idx, "name": self._tool_name,
                "query": self._tool_query,
                "start": self._tool_start_ts, "end": t,
                "elapsed": elapsed, "error": str(error)[:100],
            })
            print(f"  Error:    {str(error)[:100]}")
            print(f"  Elapsed:  {elapsed:.3f}s (failed)")
            self._tool_start_ts = None


def _last_message_content(response: dict) -> str:
    """Extract the final message content from a LangChain agent response."""
    messages = response.get("messages", [])
    if not messages:
        return ""
    return getattr(messages[-1], "content", "") or ""


def search_agent(state: dict) -> dict:
    """Use a LangChain agent to decide whether web search is needed."""
    _timer_start = time.time()
    print(f"[TIMER] search_agent START: {_timer_start:.2f}")
    print("=" * 60)
    print("PHASE 3 DIAGNOSTIC: search_agent execution trace")
    print("=" * 60)
    updated_state = dict(state)
    errors = list(updated_state.get("errors") or [])

    try:
        destination = updated_state.get("destination")
        venue = updated_state.get("venue")
        interests = updated_state.get("interests")
        trip_style = updated_state.get("trip_style")

        agent = create_agent(
            model=get_text_llm(),
            tools=[search_web],
            system_prompt=(
                "You are a destination research specialist. "
                "Your sole responsibility is destination research.\n\n"
                "Preserve every useful discovered attraction, restaurant, transportation, "
                "and local-tip detail. Remove duplicate entries only.\n\n"
                "DO NOT provide:\n"
                "- Itinerary planning or scheduling\n"
                "- Hotel or accommodation recommendations\n"
                "- Flight or airport guidance\n"
                "- Booking or reservation advice\n"
                "- Arrival, departure, or return-trip planning\n\n"
                "If your search results contain travel logistics, flights, or hotels, "
                "ignore that content entirely. Output only attractions, restaurants, "
                "local transit information, and local tips.\n\n"
                "Return markdown in exactly this structure:\n\n"
                "Venue Highlights\n\n"
                "Top Attractions\n\n"
                "* Attraction 1\n"
                "* Attraction 2\n"
                "* Attraction 3\n\n"
                "Recommended Restaurants\n\n"
                "* Restaurant 1\n"
                "* Restaurant 2\n"
                "* Restaurant 3\n\n"
                "Transportation Options\n\n"
                "* Option 1\n"
                "* Option 2\n"
                "* Option 3\n\n"
                "Local Tips\n\n"
                "* Tip 1\n"
                "* Tip 2\n"
                "* Tip 3\n\n"
                "CRITICAL: Perform exactly ONE search_web call. "
                "Formulate a single broad query covering attractions, restaurants, "
                "transportation, and local tips together. "
                "Do NOT do follow-up searches. Work with whatever the first search "
                "returns. If a category has few results, note it and move on."
            ),
        )

        prompt = (
            "Perform ONE search_web call with a broad query covering all research "
            "needs below. Do not search again regardless of results. "
            "Work with what the first search returns.\n\n"
            f"Destination: {destination}\n"
            f"Venue: {venue}\n"
            f"Interests: {interests}\n"
            f"Trip Style: {trip_style}\n\n"
            "Return a structured summary with Venue Highlights, Top Attractions, "
            "Recommended Restaurants, Transportation Options, and Local Tips. "
            "Keep all discovered useful information and remove duplicates only.\n\n"
            "Do not include flights, hotels, itinerary planning, booking advice, "
            "or any arrival/departure guidance."
        )

        trace = _SearchTraceHandler()
        response = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"callbacks": [trace]},
        )
        search_notes = _last_message_content(response)

        updated_state["search_results"] = response
        updated_state["search_notes"] = (
            search_notes or "Search agent completed without additional notes."
        )
        updated_state["search_status"] = "completed"
    except Exception as exc:
        errors.append(f"search_agent failed: {exc}")
        trace = locals().get("trace")
        updated_state["search_results"] = updated_state.get("search_results", {})
        updated_state["search_notes"] = "Web search failed."
        updated_state["search_status"] = "failed"

    # ── Trace summary (always printed, even on failure) ─────────
    if trace:
        print(f"\n{'=' * 60}")
        print("SEARCH AGENT EXECUTION TRACE")
        print(f"{'=' * 60}")
        print(f"\nChain of events:")
        print(f"  {' -> '.join(trace.chain_log)}")

        llm_count = len(trace.llm_calls)
        tool_count = len(trace.tool_calls)
        print(f"\nLLM calls:  {llm_count}")
        print(f"Tool calls: {tool_count}")

        if trace.llm_calls:
            avg_llm = sum(c["elapsed"] for c in trace.llm_calls) / llm_count
            longest_llm = max(trace.llm_calls, key=lambda c: c["elapsed"])
            print(f"Average LLM duration: {avg_llm:.3f}s")
            print(f"Longest LLM call:     LLM #{longest_llm['idx']} ({longest_llm['elapsed']:.3f}s)")

        if trace.tool_calls:
            avg_tool = sum(c["elapsed"] for c in trace.tool_calls) / tool_count
            longest_tool = max(trace.tool_calls, key=lambda c: c["elapsed"])
            print(f"Average search duration: {avg_tool:.3f}s")
            print(f"Longest search call:     Search #{longest_tool['idx']} ({longest_tool['elapsed']:.3f}s)")

        total_duration = time.time() - _timer_start
        print(f"\nTotal search_agent duration: {total_duration:.3f}s")
        print(f"{'=' * 60}\n")

    updated_state["errors"] = errors
    print(f"[TIMER] search_agent END: {time.time():.2f} (elapsed: {time.time() - _timer_start:.1f}s)")
    return updated_state

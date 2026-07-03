"""Tests for parallel fan-out execution of flight, hotel, and weather agents."""

import asyncio
import time
import unittest
import uuid
from unittest.mock import patch

from graph.trip_graph import build_trip_graph, _route_from_supervisor, _make_route_after


class TestParallelRouting(unittest.TestCase):
    """Unit tests for the parallel routing logic."""

    def setUp(self):
        self.all_enabled = {
            "run_flight_agent": True,
            "run_hotel_agent": True,
            "run_weather_agent": True,
            "run_search_agent": True,
            "run_local_agent": True,
        }
        self.none_enabled = {
            "run_flight_agent": False,
            "run_hotel_agent": False,
            "run_weather_agent": False,
            "run_search_agent": False,
            "run_local_agent": False,
        }
        self.partial_enabled = {
            "run_flight_agent": True,
            "run_hotel_agent": False,
            "run_weather_agent": True,
            "run_search_agent": True,
            "run_local_agent": True,
        }

    def test_all_five_enabled_returns_five_sends(self):
        """When all five agents are enabled, _route_from_supervisor
        returns a list of 5 Send objects."""
        result = _route_from_supervisor({"execution_plan": self.all_enabled})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 5)
        names = {s.node for s in result}
        self.assertEqual(names, {"flight_agent", "hotel_agent", "weather_agent",
                                 "search_agent", "local_agent"})

    def test_none_enabled_returns_string_itinerary_agent(self):
        """When none of the agents are enabled, route directly
        to itinerary_agent."""
        result = _route_from_supervisor({"execution_plan": self.none_enabled})
        self.assertIsInstance(result, str)
        self.assertEqual(result, "itinerary_agent")

    def test_partial_enabled_returns_only_enabled_sends(self):
        """When flight, weather, search, and local are enabled, returns 4 Send objects."""
        result = _route_from_supervisor({"execution_plan": self.partial_enabled})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 4)
        names = {s.node for s in result}
        self.assertEqual(names, {"flight_agent", "weather_agent",
                                 "search_agent", "local_agent"})

    def test_route_after_search_routes_to_local(self):
        """_make_route_after('search_agent') returns 'local_agent' when local
        is enabled."""
        state = {"execution_plan": self.all_enabled}
        router = _make_route_after("search_agent")
        result = router(state)
        self.assertEqual(result, "local_agent")

    def test_route_after_search_skips_to_itinerary(self):
        """_make_route_after('search_agent') returns 'itinerary_agent' when
        local is not enabled."""
        plan = dict(self.all_enabled)
        plan["run_local_agent"] = False
        state = {"execution_plan": plan}
        router = _make_route_after("search_agent")
        result = router(state)
        self.assertEqual(result, "itinerary_agent")

    def test_route_after_local_always_goes_to_itinerary(self):
        """_make_route_after('local_agent') always returns 'itinerary_agent'
        since local is the last sequential agent."""
        state = {"execution_plan": self.all_enabled}
        router = _make_route_after("local_agent")
        result = router(state)
        self.assertEqual(result, "itinerary_agent")


class TestParallelGraphExecution(unittest.TestCase):
    """Integration tests that build the graph and run it with patched agents
    to avoid external API dependencies."""

    def _make_mock_agent(self, name, delay=0.0):
        """Create a mock agent that sets its own fields with optional delay."""
        async def _agent(state: dict) -> dict:
            if delay:
                await asyncio.sleep(delay)
            prefix = name.split("_")[0]
            result = {}
            result[f"{prefix}_details"] = {f"{name}_data": "mock"}
            result[f"{prefix}_notes"] = f"{name} completed mock"
            result[f"{prefix}_status"] = "completed"
            result["errors"] = list(state.get("errors") or [])
            if prefix == "flight":
                result["flight_booking_link"] = "https://mock.flight"
                result["recommended_flight_price"] = 299.0
            if prefix == "hotel":
                result["hotel_booking_links"] = ["https://mock.hotel"]
                result["hotel_price_details"] = ["$$"]
            return result
        return _agent

    def _make_failing_agent(self, name):
        """Create a mock agent that always fails and appends to errors."""
        async def _agent(state: dict) -> dict:
            prefix = name.split("_")[0]
            result = {}
            result[f"{prefix}_details"] = {}
            result[f"{prefix}_notes"] = f"{name} failed."
            result[f"{prefix}_status"] = "failed"
            errors = list(state.get("errors") or [])
            errors.append(f"{name} failed mock")
            result["errors"] = errors
            return result
        return _agent

    def _make_mock_search_agent(self):
        """Mock search_agent that sets search fields."""
        async def _agent(state: dict) -> dict:
            return {
                "search_results": {"mock": True},
                "search_notes": "Mock search completed.",
                "search_status": "completed",
            }
        return _agent

    def _make_mock_local_agent(self):
        """Mock local_agent that sets local fields."""
        async def _agent(state: dict) -> dict:
            return {
                "local_results": {"mock": True},
                "local_notes": "Mock local completed.",
                "local_status": "completed",
            }
        return _agent

    def _make_mock_itinerary_agent(self):
        """Mock itinerary_agent that sets itinerary fields."""
        async def _agent(state: dict) -> dict:
            return {
                "itinerary": "Mock itinerary.",
                "itinerary_notes": "Mock itinerary notes.",
                "itinerary_status": "completed",
                "final_report": "Mock final report.",
                "status": "completed",
            }
        return _agent

    def _patch_graph_nodes(self, flight_mock, hotel_mock, weather_mock,
                           delay=0.0):
        """Return a patched graph where flight/hotel/weather agents are
        replaced with mocks. Other agents are also mocked to avoid external
        deps."""
        patcher_flight = patch(
            "graph.trip_graph.flight_agent",
            self._make_mock_agent("flight_agent", delay),
        )
        patcher_hotel = patch(
            "graph.trip_graph.hotel_agent",
            self._make_mock_agent("hotel_agent", delay),
        )
        patcher_weather = patch(
            "graph.trip_graph.weather_agent",
            self._make_mock_agent("weather_agent", delay),
        )
        patcher_search = patch(
            "graph.trip_graph.search_agent",
            self._make_mock_search_agent(),
        )
        patcher_local = patch(
            "graph.trip_graph.local_agent",
            self._make_mock_local_agent(),
        )
        patcher_itinerary = patch(
            "graph.trip_graph.itinerary_agent",
            self._make_mock_itinerary_agent(),
        )
        patcher_coordinator = patch(
            "graph.trip_graph.coordinator_agent",
            lambda s: {"status": "processing", "errors": []},
        )
        patcher_supervisor = patch(
            "graph.trip_graph.supervisor_agent",
            lambda s: {
                "execution_plan": s.get("execution_plan", {}),
                "supervisor_notes": "Mocked supervisor.",
                "errors": [],
            },
        )
        return (
            patcher_flight, patcher_hotel, patcher_weather,
            patcher_search, patcher_local, patcher_itinerary,
            patcher_coordinator, patcher_supervisor,
        )

    def _make_initial_state(self, plan):
        return {
            "origin": "Miami",
            "destination": "New York",
            "travelers": 1,
            "venue": "Madison Square Garden",
            "event_date": "2026-08-15",
            "errors": [],
            "execution_plan": plan,
        }

    def test_parallel_execution_populates_all_fields(self):
        """With all three parallel agents enabled, all state fields should
        be populated after a run."""
        plan = {
            "run_flight_agent": True,
            "run_hotel_agent": True,
            "run_weather_agent": True,
            "run_search_agent": False,
            "run_local_agent": False,
        }
        patchers = self._patch_graph_nodes(None, None, None)
        for p in patchers:
            p.start()
        try:
            graph = asyncio.run(build_trip_graph(checkpointer=None))
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            result = asyncio.run(graph.ainvoke(self._make_initial_state(plan), config))
            self.assertEqual(result.get("flight_status"), "completed")
            self.assertEqual(result.get("hotel_status"), "completed")
            self.assertEqual(result.get("weather_status"), "completed")
            self.assertIn("flight_details", result)
            self.assertIn("hotel_details", result)
            self.assertIn("weather_details", result)
        finally:
            for p in patchers:
                p.stop()

    def test_parallel_execution_faster_than_sequential(self):
        """Parallel execution of three 0.1s agents should complete in
        ~1x the single-agent time (~0.15s) rather than 3x (~0.3s)."""
        plan = {
            "run_flight_agent": True,
            "run_hotel_agent": True,
            "run_weather_agent": True,
            "run_search_agent": False,
            "run_local_agent": False,
        }
        patchers = self._patch_graph_nodes(None, None, None, delay=0.1)
        for p in patchers:
            p.start()
        try:
            graph = asyncio.run(build_trip_graph(checkpointer=None))
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            t0 = time.time()
            result = asyncio.run(graph.ainvoke(self._make_initial_state(plan), config))
            elapsed = time.time() - t0
            self.assertLess(
                elapsed, 0.25,
                f"Parallel section took {elapsed:.3f}s, "
                f"expected < 0.25s for 3 x 0.1s agents running in parallel",
            )
        finally:
            for p in patchers:
                p.stop()

    def test_skip_all_parallel_agents(self):
        """When no parallel agents are enabled, execution goes directly
        to sequential chain and completes."""
        plan = {
            "run_flight_agent": False,
            "run_hotel_agent": False,
            "run_weather_agent": False,
            "run_search_agent": False,
            "run_local_agent": False,
        }
        patchers = self._patch_graph_nodes(None, None, None)
        for p in patchers:
            p.start()
        try:
            graph = asyncio.run(build_trip_graph(checkpointer=None))
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            result = asyncio.run(graph.ainvoke(self._make_initial_state(plan), config))
            self.assertEqual(result.get("itinerary_status"), "completed")
            self.assertEqual(result.get("status"), "completed")
        finally:
            for p in patchers:
                p.stop()

    def test_errors_accumulate_from_multiple_failing_agents(self):
        """When multiple parallel agents fail, all error messages
        accumulate in errors list via the reducer."""
        plan = {
            "run_flight_agent": True,
            "run_hotel_agent": True,
            "run_weather_agent": True,
            "run_search_agent": False,
            "run_local_agent": False,
        }
        patchers = [
            patch("graph.trip_graph.flight_agent",
                  self._make_failing_agent("flight_agent")),
            patch("graph.trip_graph.hotel_agent",
                  self._make_failing_agent("hotel_agent")),
            patch("graph.trip_graph.weather_agent",
                  self._make_failing_agent("weather_agent")),
            patch("graph.trip_graph.search_agent",
                  self._make_mock_search_agent()),
            patch("graph.trip_graph.local_agent",
                  self._make_mock_local_agent()),
            patch("graph.trip_graph.itinerary_agent",
                  self._make_mock_itinerary_agent()),
            patch("graph.trip_graph.coordinator_agent",
                  lambda s: {"status": "processing", "errors": []}),
            patch("graph.trip_graph.supervisor_agent",
                  lambda s: {
                      "execution_plan": s.get("execution_plan", {}),
                      "supervisor_notes": "Mocked.",
                      "errors": [],
                  }),
        ]
        for p in patchers:
            p.start()
        try:
            graph = asyncio.run(build_trip_graph(checkpointer=None))
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            result = asyncio.run(graph.ainvoke(self._make_initial_state(plan), config))
            self.assertIn("errors", result)
            self.assertIsInstance(result["errors"], list)
            error_str = " ".join(result["errors"])
            self.assertIn("flight_agent failed mock", error_str)
            self.assertIn("hotel_agent failed mock", error_str)
            self.assertIn("weather_agent failed mock", error_str)
            self.assertEqual(len(result["errors"]), 3)
        finally:
            for p in patchers:
                p.stop()


if __name__ == "__main__":
    unittest.main()

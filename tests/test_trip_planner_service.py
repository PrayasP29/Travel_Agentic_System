import unittest
import uuid
from unittest.mock import patch

import services.trip_planner_service as service


class _StubSnapshot:
    def __init__(self, values):
        self.values = values


class _StubGraph:
    def __init__(self):
        self.invocations = []
        self.last_state_config = None

    def invoke(self, state, config=None):
        self.invocations.append((state, config))
        return {"status": "completed"}

    def get_state(self, config):
        self.last_state_config = config
        return _StubSnapshot({"status": "completed"})


class TestTripPlannerService(unittest.TestCase):
    def test_plan_trip_invokes_graph_and_returns_thread(self):
        stub_graph = _StubGraph()
        parsed = {
            "origin": "Miami",
            "destination": "New York",
            "travelers": 1,
            "venue": "Madison Square Garden",
            "event_date": "2026-08-15",
        }
        built_state = {
            "origin": "Miami",
            "destination": "New York",
            "travelers": 1,
            "venue": "Madison Square Garden",
            "event_date": "2026-08-15",
            "errors": [],
        }
        fixed_uuid = uuid.UUID("00000000-0000-0000-0000-000000000001")

        with patch.object(service, "_get_graph", return_value=stub_graph), patch.object(
            service, "request_parser_agent", return_value=parsed
        ), patch.object(service, "build_trip_state", return_value=built_state), patch.object(
            service.uuid, "uuid4", return_value=fixed_uuid
        ):
            result = service.plan_trip("Plan a trip to New York")

        self.assertEqual(result["thread_id"], "trip_00000000000000000000000000000001")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(stub_graph.invocations[0][0], built_state)
        self.assertEqual(
            stub_graph.invocations[0][1]["configurable"]["thread_id"],
            "trip_00000000000000000000000000000001",
        )

    def test_resume_trip_returns_snapshot_values(self):
        stub_graph = _StubGraph()

        with patch.object(service, "_get_graph", return_value=stub_graph):
            result = service.resume_trip("trip_test_001")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            stub_graph.last_state_config["configurable"]["thread_id"], "trip_test_001"
        )


if __name__ == "__main__":
    unittest.main()

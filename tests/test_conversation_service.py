import unittest
from unittest.mock import patch

import services.conversation_service as service


class _StubSnapshot:
    def __init__(self, values):
        self.values = values


class _StubGraph:
    def __init__(self):
        self.store = {}

    def update_state(self, config, values):
        thread_id = config["configurable"]["thread_id"]
        self.store[thread_id] = dict(values)

    def get_state(self, config):
        thread_id = config["configurable"]["thread_id"]
        return _StubSnapshot(self.store.get(thread_id, {}))


class TestConversationService(unittest.TestCase):
    def test_missing_origin(self):
        stub_graph = _StubGraph()
        parsed = {
            "origin": "",
            "destination": "New York",
            "travelers": None,
            "venue": "",
            "event_date": "2026-08-15",
        }

        with patch.object(service, "_get_graph", return_value=stub_graph), patch.object(
            service, "request_parser_agent", return_value=parsed
        ), patch.object(service, "_generate_thread_id", return_value="conversation_1"):
            result = service.start_conversation("Plan a trip to New York on 2026-08-15")

        self.assertEqual(result["status"], "collecting")
        self.assertEqual(result["missing_fields"], ["origin"])
        self.assertIsNotNone(result["next_question"])

    def test_missing_date(self):
        stub_graph = _StubGraph()
        parsed = {
            "origin": "Miami",
            "destination": "New York",
            "travelers": 1,
            "venue": "",
            "event_date": "",
        }

        with patch.object(service, "_get_graph", return_value=stub_graph), patch.object(
            service, "request_parser_agent", return_value=parsed
        ), patch.object(service, "_generate_thread_id", return_value="conversation_2"):
            result = service.start_conversation("Plan a trip from Miami to New York")

        self.assertEqual(result["status"], "collecting")
        self.assertEqual(result["missing_fields"], ["event_date"])
        self.assertIsNotNone(result["next_question"])

    def test_resume_conversation(self):
        stub_graph = _StubGraph()
        stub_graph.update_state(
            {"configurable": {"thread_id": "conversation_3"}},
            {
                "origin": "",
                "destination": "New York",
                "event_date": "2026-08-15",
                "travelers": 1,
                "venue": "",
                "errors": [],
                "status": "collecting",
            },
        )

        with patch.object(service, "_get_graph", return_value=stub_graph):
            result = service.resume_conversation("conversation_3")

        self.assertEqual(result["status"], "collecting")
        self.assertEqual(result["missing_fields"], ["origin"])

    def test_complete_planning_flow(self):
        stub_graph = _StubGraph()
        parsed_start = {
            "origin": "Miami",
            "destination": "",
            "travelers": 1,
            "venue": "",
            "event_date": "2026-08-15",
        }
        parsed_continue = {
            "origin": "",
            "destination": "New York",
            "travelers": None,
            "venue": "",
            "event_date": "",
        }

        with patch.object(service, "_get_graph", return_value=stub_graph), patch.object(
            service, "_generate_thread_id", return_value="conversation_4"
        ), patch.object(
            service, "request_parser_agent", side_effect=[parsed_start, parsed_continue]
        ), patch.object(
            service, "plan_trip", return_value={"status": "completed", "thread_id": "plan_1"}
        ):
            start_result = service.start_conversation(
                "Plan a trip from Miami on 2026-08-15"
            )
            self.assertEqual(start_result["status"], "collecting")

            continue_result = service.continue_conversation(
                "conversation_4", "Destination is New York"
            )

        self.assertEqual(continue_result["status"], "completed")
        self.assertEqual(continue_result["plan_result"]["thread_id"], "plan_1")

    def test_conversation_state_corruption_fix(self):
        stub_graph = _StubGraph()
        parsed_start = {
            "origin": "",
            "destination": "New York",
            "travelers": 1,
            "venue": "",
            "event_date": "",
        }
        parsed_date = {
            "origin": "",
            "destination": "",
            "travelers": None,
            "venue": "",
            "event_date": "2026-08-15",
        }

        with patch.object(service, "_get_graph", return_value=stub_graph), patch.object(
            service, "_generate_thread_id", return_value="conversation_5"
        ), patch.object(
            service, "request_parser_agent", side_effect=[parsed_start, parsed_date]
        ), patch.object(
            service, "plan_trip", return_value={"status": "completed", "thread_id": "plan_5"}
        ):
            # 1. Start with "Plan a trip to New York"
            start_result = service.start_conversation("Plan a trip to New York")
            self.assertEqual(start_result["status"], "collecting")
            self.assertEqual(start_result["missing_fields"], ["origin", "event_date"])
            self.assertEqual(start_result["state"]["destination"], "New York")
            self.assertEqual(start_result["state"]["origin"], "")

            # 2. Reply "Miami"
            continue_result_1 = service.continue_conversation(
                "conversation_5", "Miami"
            )
            self.assertEqual(continue_result_1["status"], "collecting")
            self.assertEqual(continue_result_1["missing_fields"], ["event_date"])
            self.assertEqual(continue_result_1["state"]["origin"], "Miami")
            self.assertEqual(continue_result_1["state"]["destination"], "New York")

            # 3. Reply "August 15 2026"
            continue_result_2 = service.continue_conversation(
                "conversation_5", "August 15 2026"
            )
            
            self.assertEqual(continue_result_2["status"], "completed")
            self.assertEqual(continue_result_2["state"]["origin"], "Miami")
            self.assertEqual(continue_result_2["state"]["destination"], "New York")
            self.assertEqual(continue_result_2["state"]["event_date"], "2026-08-15")
            self.assertEqual(continue_result_2["plan_result"]["thread_id"], "plan_5")

    def test_date_normalization_formats(self):
        self.assertEqual(service._normalize_event_date("August 15 2026"), "2026-08-15")
        self.assertEqual(service._normalize_event_date("2026-08-15"), "2026-08-15")
        self.assertEqual(service._normalize_event_date("15 Aug 2026"), "2026-08-15")
        self.assertEqual(service._normalize_event_date("august 15 2026"), "2026-08-15")
        self.assertEqual(service._normalize_event_date("15th August 2026"), "2026-08-15")


if __name__ == "__main__":
    unittest.main()

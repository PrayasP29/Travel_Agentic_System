import unittest

from utils.state_builder import build_trip_state


class TestStateBuilder(unittest.TestCase):
    def test_build_trip_state_populates_fields(self):
        parsed = {
            "origin": "Miami",
            "destination": "New York",
            "travelers": "2",
            "venue": "Madison Square Garden",
            "event_date": "2026-08-15",
        }

        state = build_trip_state(parsed)

        self.assertEqual(state["origin"], "Miami")
        self.assertEqual(state["destination"], "New York")
        self.assertEqual(state["travelers"], 2)
        self.assertEqual(state["venue"], "Madison Square Garden")
        self.assertEqual(state["event_date"], "2026-08-15")
        self.assertEqual(state["errors"], [])

    def test_build_trip_state_defaults_travelers(self):
        parsed = {
            "destination": "New York",
            "venue": "Madison Square Garden",
            "event_date": "2026-08-15",
        }

        state = build_trip_state(parsed)

        self.assertEqual(state["travelers"], 1)
        self.assertEqual(state["errors"], [])

    def test_build_trip_state_rejects_invalid_travelers(self):
        with self.assertRaises(ValueError):
            build_trip_state(
                {
                    "destination": "New York",
                    "travelers": 0,
                }
            )


if __name__ == "__main__":
    unittest.main()

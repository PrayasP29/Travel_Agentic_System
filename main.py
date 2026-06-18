"""Command-line entry point for running the trip planner."""

from __future__ import annotations

import argparse

from services.trip_planner_service import plan_trip


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan a trip from a user request.")
    parser.add_argument(
        "--request",
        required=True,
        help="Natural-language trip request.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = plan_trip(args.request)
    print(result.get("final_report", ""))


if __name__ == "__main__":
    main()

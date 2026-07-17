"""Execution visibility logger for graph workflow.

Provides a dedicated INFO-level logger for observing graph execution
in the terminal. This is a developer observability feature only — it
never influences execution, never modifies state, and never touches SSE.

# ponytail: stdlib logging, one handler, no classes, no abstractions.
# Upgrade path: structured JSON logging or OpenTelemetry traces.
"""

import logging
import sys

logger = logging.getLogger("trip_planner.execution")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)

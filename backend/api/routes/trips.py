import uuid

from fastapi import APIRouter, Body, Path

from backend.api.log_config import logger
from agents.request_parser_agent import request_parser_agent
from backend.api.schemas.request import TripPlanRequest
from backend.api.schemas.response import (
    HealthResponse,
    TripPlanResponse,
    TripStateResponse,
)
from services.trip_planner_service import resume_trip as load_trip_checkpoint
from utils.state_builder import build_trip_state

router = APIRouter(prefix="/api/trips", tags=["Trip Planning"])

_GRAPH_INSTANCE = None


async def _get_graph():
    global _GRAPH_INSTANCE
    if _GRAPH_INSTANCE is None:
        from graph.trip_graph import build_trip_graph

        _GRAPH_INSTANCE = await build_trip_graph()
    return _GRAPH_INSTANCE


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns a simple health indicator to confirm the API is running and reachable.",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {"status": "healthy"}
                }
            },
        }
    },
)
def health_check() -> HealthResponse:
    return HealthResponse(status="healthy")


@router.post(
    "/plan",
    response_model=TripPlanResponse,
    summary="Plan a new trip",
    description=(
        "Accepts structured trip details (origin, destination, event date, venue) "
        "or a natural-language sentence. A sentence is parsed by the LLM request "
        "parser agent into structured fields, then the multi-agent trip-planning "
        "graph is invoked. Returns a markdown travel report, suggested itinerary, "
        "and execution metadata."
    ),
    responses={
        200: {
            "description": "Trip-planning graph executed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "report": (
                            "# Executive Travel Report\n\n"
                            "## Trip Overview\n\n"
                            "* Origin: MIA\n"
                            "* Destination: EWR\n"
                            "* Event Date: 2026-07-15\n\n"
                            "..."
                        ),
                        "itinerary": "**Day 1** – Arrive...\n**Day 2** – Event...",
                        "destination": "EWR",
                        "event_date": "2026-07-15",
                    }
                }
            },
        },
        422: {
            "description": "Validation error – missing or invalid request fields",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "origin"],
                                "msg": "field required",
                                "type": "value_error.missing",
                            }
                        ]
                    }
                }
            },
        },
        500: {
            "description": "Internal error during graph execution",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "report": "Graph execution failed: ...",
                        "itinerary": "",
                        "destination": "EWR",
                        "event_date": "2026-07-15",
                    }
                }
            },
        },
    },
)
async def plan_trip(
    body: TripPlanRequest = Body(...),
) -> TripPlanResponse:
    if body.sentence:
        logger.info(f"Parsing natural-language request: {body.sentence!r}")
        parsed = request_parser_agent(body.sentence)
    else:
        parsed = {
            "origin": body.origin,
            "destination": body.destination,
            "event_date": body.event_date,
            "venue": body.venue,
        }

    destination = parsed.get("destination", "")
    event_date = parsed.get("event_date", "")

    state = build_trip_state(parsed)
    thread_id = f"api_trip_{uuid.uuid4().hex}"

    try:
        logger.info(f"thread_id={thread_id} origin={parsed.get('origin')} destination={destination} | Invoking graph")
        graph = await _get_graph()
        result = await graph.ainvoke(
            state,
            config={"configurable": {"thread_id": thread_id}},
        )
    except Exception as exc:
        logger.exception(f"thread_id={thread_id} | Graph execution failed: {exc}")
        return TripPlanResponse(
            success=False,
            report=f"Graph execution failed: {exc}",
            itinerary="",
            destination=destination,
            event_date=event_date,
        )

    if not isinstance(result, dict):
        logger.error(f"thread_id={thread_id} | Graph returned unexpected type: {type(result)}")
        return TripPlanResponse(
            success=False,
            report="Graph returned unexpected type",
            itinerary="",
            destination=destination,
            event_date=event_date,
        )

    status = result.get("status", "unknown")
    logger.info(
        f"thread_id={thread_id} status={status} "
        f"has_report={bool(result.get('final_report'))} "
        f"has_itinerary={bool(result.get('itinerary'))} | Graph completed"
    )

    report = result.get("final_report", "")
    itinerary = result.get("itinerary", "")

    return TripPlanResponse(
        success=True,
        report=report,
        itinerary=itinerary,
        destination=destination,
        event_date=event_date,
    )


@router.get(
    "/{thread_id}",
    response_model=TripStateResponse,
    summary="Get trip state by thread ID",
    description=(
        "Retrieves the persisted internal state of a previously executed "
        "trip-planning run using its unique thread identifier."
    ),
    responses={
        200: {
            "description": "State retrieved successfully (may be empty if thread not found)",
            "content": {
                "application/json": {
                    "example": {
                        "thread_id": "api_trip_a1b2c3d4e5f6",
                        "status": "completed",
                        "state": {
                            "destination": "EWR",
                            "status": "completed",
                        },
                    }
                }
            },
        },
        404: {
            "description": "Thread ID not found in persistence store",
            "content": {
                "application/json": {
                    "example": {
                        "thread_id": "api_trip_nonexistent",
                        "status": "not_found",
                        "state": {},
                    }
                }
            },
        },
    },
)
async def get_trip_state(
    thread_id: str = Path(
        ...,
        title="Trip thread ID",
        description="Unique thread identifier assigned to a trip-planning workflow.",
        examples=["api_trip_a1b2c3d4e5f6"],
        min_length=1,
    ),
) -> TripStateResponse:
    try:
        state = await load_trip_checkpoint(thread_id)
    except Exception:
        return TripStateResponse(
            thread_id=thread_id, status="not_found", state={}
        )

    if not isinstance(state, dict):
        return TripStateResponse(
            thread_id=thread_id, status="unknown", state={}
        )

    return TripStateResponse(
        thread_id=thread_id,
        status=state.get("status", "unknown"),
        state=state,
    )


@router.post(
    "/{thread_id}/resume",
    response_model=TripStateResponse,
    summary="Resume a trip-planning run",
    description=(
        "Resumes execution of a previously started trip-planning workflow "
        "from its last persisted checkpoint. "
        "If the run has already completed or failed, the current state is returned as-is."
    ),
    responses={
        200: {
            "description": "Trip resumed and state returned",
            "content": {
                "application/json": {
                    "example": {
                        "thread_id": "api_trip_a1b2c3d4e5f6",
                        "status": "completed",
                        "state": {
                            "destination": "EWR",
                            "status": "completed",
                        },
                    }
                }
            },
        },
        404: {
            "description": "Thread ID not found",
            "content": {
                "application/json": {
                    "example": {
                        "thread_id": "api_trip_nonexistent",
                        "status": "not_found",
                        "state": {},
                    }
                }
            },
        },
    },
)
async def resume_trip_execution(
    thread_id: str = Path(
        ...,
        title="Trip thread ID",
        description="Unique thread identifier of the workflow to resume.",
        examples=["api_trip_a1b2c3d4e5f6"],
        min_length=1,
    ),
) -> TripStateResponse:
    try:
        current = await load_trip_checkpoint(thread_id)
    except Exception:
        return TripStateResponse(
            thread_id=thread_id, status="not_found", state={}
        )

    if not isinstance(current, dict):
        return TripStateResponse(
            thread_id=thread_id, status="unknown", state={}
        )

    current_status = current.get("status", "")

    if current_status in ("completed", "failed", "not_found"):
        return TripStateResponse(
            thread_id=thread_id,
            status=current_status,
            state=current,
        )

    try:
        graph = await _get_graph()
        result = await graph.ainvoke(
            current,
            config={"configurable": {"thread_id": thread_id}},
        )
    except Exception as exc:
        return TripStateResponse(
            thread_id=thread_id,
            status="failed",
            state=current,
        )
    except BaseException as exc:
        return TripStateResponse(
            thread_id=thread_id,
            status="failed",
            state={"error": str(exc)},
        )

    if not isinstance(result, dict):
        return TripStateResponse(
            thread_id=thread_id, status="unknown", state={}
        )

    return TripStateResponse(
        thread_id=thread_id,
        status=result.get("status", "completed"),
        state=result,
    )

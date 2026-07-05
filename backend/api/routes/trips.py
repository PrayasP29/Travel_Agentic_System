import uuid
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.log_config import logger
from agents.request_parser_agent import request_parser_agent
from backend.api.schemas.request import TripPlanRequest
from backend.api.schemas.response import (
    HealthResponse,
    TripDetailResponse,
    TripHistoryItem,
    TripPlanResponse,
    TripStateResponse,
)
from services.trip_planner_service import resume_trip as load_trip_checkpoint
from utils.state_builder import build_trip_state
from auth.dependencies import get_current_active_user
from database.connection import get_db
from database.crud import (
    create_trip,
    get_trip_by_id,
    get_trip_by_thread_id,
    get_user_trips,
    update_trip_status,
)
from database.models import User

router = APIRouter(prefix="/trips", tags=["Trip Planning"])

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
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
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
    thread_id = f"{current_user.id}-{uuid.uuid4().hex}"

    trip = await create_trip(
        db,
        user_id=current_user.id,
        request_text=body.sentence or f"Trip from {parsed.get('origin', '')} to {parsed.get('destination', '')}",
        origin=parsed.get("origin", ""),
        destination=parsed.get("destination", ""),
        event_date=parsed.get("event_date", ""),
        venue=parsed.get("venue", ""),
        travelers=parsed.get("travelers", 1),
        thread_id=thread_id,
    )

    try:
        logger.info(f"thread_id={thread_id} origin={parsed.get('origin')} destination={destination} | Invoking graph")
        graph = await _get_graph()
        result = await graph.ainvoke(
            state,
            config={"configurable": {"thread_id": thread_id}},
        )
    except Exception as exc:
        logger.exception(f"thread_id={thread_id} | Graph execution failed: {exc}")
        await update_trip_status(db, trip_id=trip.id, status="failed")
        return TripPlanResponse(
            success=False,
            report=f"Graph execution failed: {exc}",
            itinerary="",
            destination=destination,
            event_date=event_date,
            trip_id=trip.id,
            thread_id=thread_id,
        )

    if not isinstance(result, dict):
        logger.error(f"thread_id={thread_id} | Graph returned unexpected type: {type(result)}")
        await update_trip_status(db, trip_id=trip.id, status="failed")
        return TripPlanResponse(
            success=False,
            report="Graph returned unexpected type",
            itinerary="",
            destination=destination,
            event_date=event_date,
            trip_id=trip.id,
            thread_id=thread_id,
        )

    await update_trip_status(
        db,
        trip_id=trip.id,
        status="completed",
        final_state=result,
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
        trip_id=trip.id,
        thread_id=thread_id,
    )


@router.get(
    "/history",
    response_model=list[TripHistoryItem],
    summary="List trips for current user",
    description="Returns a paginated list of trips belonging to the authenticated user, ordered by creation date descending.",
)
async def list_trips(
    limit: int = Query(default=20, ge=1, le=50, description="Number of trips to return."),
    offset: int = Query(default=0, ge=0, description="Number of trips to skip."),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[TripHistoryItem]:
    trips = await get_user_trips(db, current_user.id, limit=limit, offset=offset)
    return [TripHistoryItem.model_validate(t) for t in trips]


@router.get(
    "/{identifier}",
    response_model=TripDetailResponse | TripStateResponse,
    summary="Get trip detail by ID or state by thread ID",
    description=(
        "If the identifier is a valid UUID, returns the full trip record "
        "(authenticated). Otherwise returns the persisted LangGraph workflow state."
    ),
)
async def get_trip_or_state(
    identifier: str = Path(
        ...,
        title="Trip ID or thread ID",
        description="UUID of the trip record or string thread identifier.",
        min_length=1,
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TripDetailResponse | TripStateResponse:
    try:
        trip_id = UUID(identifier)
    except ValueError:
        state = await load_trip_checkpoint(identifier)
        if not isinstance(state, dict):
            return TripStateResponse(
                thread_id=identifier, status="not_found", state={}
            )
        return TripStateResponse(
            thread_id=identifier,
            status=state.get("status", "unknown"),
            state=state,
        )

    trip = await get_trip_by_id(db, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if str(trip.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return TripDetailResponse.model_validate(trip)


@router.post(
    "/{thread_id}/resume",
    response_model=TripStateResponse,
    summary="Resume a trip-planning run",
    description=(
        "Resumes execution of a previously started trip-planning workflow "
        "from its last persisted checkpoint. "
        "If the run has already completed or failed, the current state is returned as-is."
    ),
)
async def resume_trip_execution(
    thread_id: str = Path(
        ...,
        title="Trip thread ID",
        description="Unique thread identifier of the workflow to resume.",
        examples=["api_trip_a1b2c3d4e5f6"],
        min_length=1,
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TripStateResponse:
    trip = await get_trip_by_thread_id(db, thread_id)
    if not trip or str(trip.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

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
        await update_trip_status(db, trip_id=trip.id, status="failed")
        return TripStateResponse(
            thread_id=thread_id,
            status="failed",
            state=current,
        )

    if not isinstance(result, dict):
        await update_trip_status(db, trip_id=trip.id, status="failed")
        return TripStateResponse(
            thread_id=thread_id, status="unknown", state={}
        )

    await update_trip_status(
        db,
        trip_id=trip.id,
        status="completed",
        final_state=result,
    )

    return TripStateResponse(
        thread_id=thread_id,
        status=result.get("status", "completed"),
        state=result,
    )

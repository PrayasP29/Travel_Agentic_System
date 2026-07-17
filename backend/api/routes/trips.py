import json
import time
import uuid
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.log_config import logger
from agents.request_parser_agent import (
    request_parser_agent,
    validate_parsed_fields,
    format_missing_fields_message,
)
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
from services.rate_limiter import (
    check_trip_failure_rate_limit,
    check_trip_quota,
    record_trip_failure,
    record_trip_success,
    reset_trip_failures,
)
from utils.error_categories import classify_error

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
    user_id = str(current_user.id)
    await check_trip_failure_rate_limit(user_id)
    await check_trip_quota(user_id)

    if body.sentence:
        logger.info(f"Parsing natural-language request: {body.sentence!r}")
        try:
            parsed = request_parser_agent(body.sentence)
        except Exception:
            parsed = {}
        missing = validate_parsed_fields(parsed)
        if missing:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": format_missing_fields_message(missing)},
            )
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
        await record_trip_failure(user_id)
        return TripPlanResponse(
            success=False,
            report=classify_error(exc, "graph"),
            itinerary="",
            destination=destination,
            event_date=event_date,
            trip_id=trip.id,
            thread_id=thread_id,
        )

    if not isinstance(result, dict):
        logger.error(f"thread_id={thread_id} | Graph returned unexpected type: {type(result)}")
        await update_trip_status(db, trip_id=trip.id, status="failed")
        await record_trip_failure(user_id)
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

    await record_trip_success(user_id)
    await reset_trip_failures(user_id)

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


@router.post(
    "/plan/stream",
    response_class=StreamingResponse,
    summary="Plan a trip with real-time progress streaming",
    description=(
        "Same as POST /trips/plan but streams progress events via "
        "Server-Sent Events instead of blocking until completion. "
        "Progress events are emitted as each agent starts and completes. "
        "The final event contains the same payload as TripPlanResponse."
    ),
)
async def plan_trip_stream(
    body: TripPlanRequest = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    user_id = str(current_user.id)
    await check_trip_failure_rate_limit(user_id)
    await check_trip_quota(user_id)

    if body.sentence:
        logger.info(f"Parsing natural-language request: {body.sentence!r}")
        try:
            parsed = request_parser_agent(body.sentence)
        except Exception:
            parsed = {}
        missing = validate_parsed_fields(parsed)
        if missing:
            message = format_missing_fields_message(missing)

            async def _validation_error_stream():
                yield f"event: error\ndata: {json.dumps({'success': False, 'message': message})}\n\n"

            return StreamingResponse(
                _validation_error_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
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

    _NODE_LABELS = {
        "coordinator_agent": "Coordinator",
        "supervisor_agent": "Supervisor",
        "flight_agent": "Flight",
        "hotel_agent": "Hotel",
        "weather_agent": "Weather",
        "search_agent": "Search",
        "local_agent": "Local",
        "itinerary_agent": "Itinerary",
    }
    _CACHEABLE = {"flight_agent", "hotel_agent", "weather_agent", "search_agent", "itinerary_agent"}
    _STATUS_KEYS = {
        "flight": "flight_status",
        "hotel": "hotel_status",
        "weather": "weather_status",
        "search": "search_status",
        "local": "local_status",
        "itinerary": "itinerary_status",
    }
    _NOTES_KEYS = {
        "flight": "flight_notes",
        "hotel": "hotel_notes",
        "weather": "weather_notes",
        "search": "search_notes",
        "local": "local_notes",
    }

    async def _event_generator():
        def _sse(event_type: str, data: dict) -> str:
            return f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"

        yield _sse("progress", {"step": "request_received", "message": "Request received"})

        node_times: dict[str, float] = {}
        final_state: dict | None = None
        accumulated: dict = dict(state)

        try:
            graph = await _get_graph()
            async for event in graph.astream_events(
                state,
                config={"configurable": {"thread_id": thread_id}},
                version="v2",
            ):
                kind = event.get("event", "")
                name = event.get("name", "")
                parent = event.get("parent_run_id")

                if kind == "on_chain_end" and parent is None:
                    final_state = event.get("data", {}).get("output")
                    continue

                if name not in _NODE_LABELS:
                    continue

                label = _NODE_LABELS[name]
                ctx = name.replace("_agent", "")

                if kind == "on_chain_start":
                    node_times[name] = time.monotonic()
                    yield _sse("progress", {
                        "step": f"{label.lower()}_started",
                        "message": f"{label} started",
                    })

                elif kind == "on_chain_end":
                    elapsed = time.monotonic() - node_times.get(name, time.monotonic())
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict):
                        accumulated.update({k: v for k, v in output.items() if k != "errors"})
                        accumulated.setdefault("errors", []).extend(output.get("errors", []))

                    status_key = _STATUS_KEYS.get(ctx)
                    agent_status = accumulated.get(status_key) if status_key else None

                    if agent_status == "failed":
                        notes_key = _NOTES_KEYS.get(ctx)
                        error_msg = accumulated.get(
                            notes_key,
                            classify_error(Exception("Agent failed"), ctx),
                        )
                        yield _sse("progress", {
                            "step": f"{label.lower()}_failed",
                            "message": error_msg,
                        })
                    elif name in _CACHEABLE and elapsed < 0.5:
                        yield _sse("progress", {
                            "step": f"{label.lower()}_cache_hit",
                            "message": f"{label} → cache hit",
                        })
                    else:
                        yield _sse("progress", {
                            "step": f"{label.lower()}_completed",
                            "message": f"{label} completed",
                        })

                elif kind == "on_chain_error":
                    raw_err = event.get("data", {}).get("error", Exception("Agent failed"))
                    if not isinstance(raw_err, Exception):
                        raw_err = Exception(str(raw_err))
                    yield _sse("progress", {
                        "step": f"{label.lower()}_failed",
                        "message": classify_error(raw_err, ctx),
                    })

        except Exception as exc:
            yield _sse("error", {"message": classify_error(exc, "graph")})
            await update_trip_status(db, trip_id=trip.id, status="failed")
            await record_trip_failure(user_id)
            return

        result_state = final_state or accumulated

        await update_trip_status(
            db, trip_id=trip.id, status="completed", final_state=result_state,
        )
        await record_trip_success(user_id)
        await reset_trip_failures(user_id)

        logger.info(
            f"thread_id={thread_id} status={result_state.get('status', 'unknown')} "
            f"has_report={bool(result_state.get('final_report'))} "
            f"has_itinerary={bool(result_state.get('itinerary'))} | Stream completed"
        )

        yield _sse("done", {
            "success": True,
            "report": result_state.get("final_report", ""),
            "itinerary": result_state.get("itinerary", ""),
            "destination": destination,
            "event_date": event_date,
            "trip_id": str(trip.id),
            "thread_id": thread_id,
        })

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
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

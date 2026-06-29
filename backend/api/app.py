import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.log_config import logger, request_id_var
from backend.api.routes.trips import router as trips_router


# ---------------------------------------------------------------------------
# Middleware – request ID & timing logging
# ---------------------------------------------------------------------------

async def _logging_middleware(request: Request, call_next):
    request_id = uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    request_id_var.set(request_id)

    start = time.monotonic()

    try:
        response = await call_next(request)
    except BaseException:
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        logger.exception(
            "Unhandled exception in middleware | "
            f"method={request.method} path={request.url.path} "
            f"elapsed_ms={elapsed_ms}"
        )
        raise

    elapsed_ms = round((time.monotonic() - start) * 1000, 2)
    logger.info(
        f"method={request.method} path={request.url.path} "
        f"status_code={response.status_code} elapsed_ms={elapsed_ms} | "
        f"Request completed"
    )
    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


async def _validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning(
        f"method={request.method} path={request.url.path} | "
        f"Validation error: {exc.errors()}"
    )
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": exc.errors()}),
    )


async def _http_error_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    logger.warning(
        f"method={request.method} path={request.url.path} "
        f"status_code={exc.status_code} | HTTP error: {exc.detail}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"detail": exc.detail}),
    )


async def _global_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(
        f"method={request.method} path={request.url.path} "
        f"type={type(exc).__name__} | Unhandled exception"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."},
    )


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(
        title="Trip Planner API",
        description=(
            "Multi-agent travel planning backend. "
            "Accepts a trip request (origin, destination, date, venue), "
            "orchestrates specialist agents for flights, hotels, weather, "
            "local attractions, and itinerary generation, then returns a "
            "comprehensive markdown travel report."
        ),
        version="2.0.0",
        contact={
            "name": "Travel Agentic System",
            "url": "https://github.com/anomalyco/Travel_Agentic_System",
        },
        license_info={
            "name": "MIT",
            "identifier": "MIT",
        },
        openapi_tags=[
            {
                "name": "Trip Planning",
                "description": (
                    "Create trip plans, inspect persisted workflow state, "
                    "resume interrupted runs, and check API health."
                ),
            }
        ],
    )

    app.middleware("http")(_logging_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://172.20.10.11:8080",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(HTTPException, _http_error_handler)
    app.add_exception_handler(Exception, _global_error_handler)

    app.include_router(trips_router)

    return app


app = create_app()

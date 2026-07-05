from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health status returned when the API is reachable."""

    status: str = Field(
        title="Status",
        description="Current API health indicator.",
        examples=["healthy"],
    )

    model_config = {
        "json_schema_extra": {"examples": [{"status": "healthy"}]}
    }


class TripPlanResponse(BaseModel):
    """Final report and itinerary returned after trip planning completes."""

    success: bool = Field(
        title="Success",
        description="Whether the trip-planning graph completed without a top-level error.",
        examples=[True],
    )
    report: str = Field(
        title="Report",
        description="Markdown-formatted travel report assembled from agent outputs.",
        examples=["# Executive Travel Report\n\n## Trip Overview\n..."],
    )
    itinerary: str = Field(
        title="Itinerary",
        description="Suggested day-by-day itinerary in markdown (may be empty on failure).",
        examples=["**Day 1** – Arrive at Newark Airport..."],
    )
    destination: str = Field(
        title="Destination",
        description="Destination airport or city IATA code from the original request.",
        examples=["EWR"],
    )
    event_date: str = Field(
        title="Event Date",
        description="Travel date in YYYY-MM-DD format from the original request.",
        examples=["2026-07-15"],
    )
    trip_id: UUID | None = Field(
        default=None,
        title="Trip ID",
        description="Database primary key of the created trip record.",
    )
    thread_id: str | None = Field(
        default=None,
        title="Thread ID",
        description="LangGraph thread identifier for the planning session.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "report": (
                        "# Executive Travel Report\n\n"
                        "## Trip Overview\n\n"
                        "* Origin: MIA\n"
                        "* Destination: EWR\n"
                        "* Venue: Prudential Center\n"
                        "* Event Date: 2026-07-15\n\n"
                        "## Flight Information\n\n"
                        "The flight details below...\n\n"
                        "Flight 1\n\n"
                        "Route:\nMIA → EWR\n\n"
                        "Departure Time:\n10:30 AM\n\n"
                        "Arrival Time:\n12:45 PM\n\n"
                        "Duration:\n2h 15m\n\n"
                        "Price:\n150 EUR\n\n"
                        "Booking Link:\nhttps://example.com/book\n"
                    ),
                    "itinerary": (
                        "**Day 1** – Arrive at Newark Airport, check in, "
                        "explore local area.\n"
                        "**Day 2** – Attend event at Prudential Center.\n"
                        "**Day 3** – Depart."
                    ),
                    "destination": "EWR",
                    "event_date": "2026-07-15",
                }
            ]
        }
    }


class TripStateResponse(BaseModel):
    """Persisted workflow state returned when a trip is queried or resumed."""

    thread_id: str = Field(
        title="Thread ID",
        description="Unique identifier for the trip-planning session.",
        examples=["api_trip_a1b2c3d4e5f6"],
    )
    status: str = Field(
        title="Status",
        description=(
            "Current state of the trip-planning workflow. "
            "Typical values: pending, running, completed, failed, not_found."
        ),
        examples=["completed"],
    )
    state: dict = Field(
        title="State",
        description=(
            "Full internal state dictionary of the trip-planning graph. "
            "Includes agent outputs, notes, and execution metadata."
        ),
        examples=[{"destination": "EWR", "status": "completed", "flight_notes": "..."}],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "thread_id": "api_trip_a1b2c3d4e5f6",
                    "status": "completed",
                    "state": {
                        "destination": "EWR",
                        "status": "completed",
                    },
                }
            ]
        }
    }


class TripHistoryItem(BaseModel):
    """Lightweight trip record returned in the history list (no report body)."""

    id: UUID = Field(title="Trip ID", description="Database primary key.")
    request_text: str | None = Field(title="Request text", description="Original user request.")
    origin: str | None = Field(title="Origin", description="Departure location.")
    destination: str | None = Field(title="Destination", description="Arrival location.")
    status: str = Field(title="Status", description="Current trip status.")
    created_at: datetime | None = Field(title="Created at", description="When the trip was created.")
    completed_at: datetime | None = Field(title="Completed at", description="When the trip finished.")

    class Config:
        from_attributes = True


class TripDetailResponse(BaseModel):
    """Full trip record including agent outputs."""

    id: UUID = Field(title="Trip ID")
    user_id: UUID = Field(title="User ID")
    request_text: str | None = Field(title="Request text")
    origin: str | None = Field(title="Origin")
    destination: str | None = Field(title="Destination")
    event_date: str | None = Field(title="Event date")
    venue: str | None = Field(title="Venue")
    travelers: int = Field(default=1, title="Travelers")
    status: str = Field(title="Status")
    final_report: str | None = Field(title="Final report", description="Markdown travel report.")
    flight_details: dict | None = Field(title="Flight details")
    hotel_details: dict | None = Field(title="Hotel details")
    weather_details: dict | None = Field(title="Weather details")
    thread_id: str | None = Field(title="Thread ID")
    created_at: datetime | None = Field(title="Created at")
    completed_at: datetime | None = Field(title="Completed at")

    class Config:
        from_attributes = True

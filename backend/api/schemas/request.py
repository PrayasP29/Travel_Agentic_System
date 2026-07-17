from pydantic import BaseModel, Field, model_validator


class TripPlanRequest(BaseModel):
    origin: str | None = Field(
        None,
        title="Origin",
        description="Departure airport or city IATA code (e.g. MIA, JFK, LHR).",
        example="MIA",
        min_length=3,
    )
    destination: str | None = Field(
        None,
        title="Destination",
        description="Arrival airport or city IATA code (e.g. EWR, LAX, CDG).",
        example="EWR",
        min_length=3,
    )
    event_date: str | None = Field(
        None,
        title="Event Date",
        description="Date of travel or the destination event in YYYY-MM-DD format.",
        example="2026-07-15",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    venue: str | None = Field(
        None,
        title="Venue",
        description="Name of the venue or event being attended at the destination.",
        example="Prudential Center",
        min_length=1,
    )
    sentence: str | None = Field(
        None,
        title="Natural-language trip request",
        description=(
            "A free-text description of the trip, e.g. "
            "'I want to fly from Mumbai to Delhi on 2026-07-15 for a concert.'"
        ),
        example="I want to fly from Mumbai to Delhi on 2026-07-15 for a concert at the Dome.",
        min_length=1,
    )

    @model_validator(mode="after")
    def check_payload(self):
        if self.sentence:
            return self
        if self.origin and self.destination and self.event_date and self.venue:
            return self
        raise ValueError(
            "Either provide 'sentence' (natural language) or all structured fields: "
            "origin, destination, event_date, venue"
        )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "origin": "MIA",
                    "destination": "EWR",
                    "event_date": "2026-07-15",
                    "venue": "Prudential Center",
                },
                {
                    "sentence": "I want to fly from Mumbai to Delhi on 2026-07-15 for a concert at the Dome.",
                },
            ]
        }
    }

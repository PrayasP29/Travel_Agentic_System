"""Centralized cache key generation helpers and TTL constants.

All keys are prefixed to avoid collisions. Usage:
    key = CacheKeys.flight("MIA", "EWR", "2026-08-01", "1")
"""

# Cache TTLs in seconds
FLIGHT_TTL = 600       # 10 minutes
HOTEL_TTL = 1200       # 20 minutes
WEATHER_TTL = 3600     # 60 minutes
SEARCH_TTL = 43200     # 12 hours
ITINERARY_TTL = 600    # 10 minutes


class CacheKeys:
    PREFIX = "tripplanner"

    @staticmethod
    def _make(namespace: str, *parts: str) -> str:
        return f"{CacheKeys.PREFIX}:{namespace}:{':'.join(parts)}"

    @classmethod
    def flight(cls, origin: str, destination: str, event_date: str, travelers: str) -> str:
        return cls._make("flight", origin, destination, event_date, travelers)

    @classmethod
    def hotel(cls, destination: str, event_date: str, travelers: str) -> str:
        return cls._make("hotel", destination, event_date, travelers)

    @classmethod
    def weather(cls, destination: str, event_date: str) -> str:
        return cls._make("weather", destination, event_date)

    @classmethod
    def search(cls, destination: str, venue: str) -> str:
        return cls._make("search", destination, venue)

    @classmethod
    def itinerary(cls, destination: str, venue: str, event_date: str) -> str:
        return cls._make("itinerary", destination, venue, event_date)

    # Rate limit keys
    @classmethod
    def login(cls, email: str) -> str:
        return cls._make("login", email)

    @classmethod
    def login_lock(cls, email: str) -> str:
        return cls._make("login_lock", email)

    @classmethod
    def register(cls, email: str) -> str:
        return cls._make("register", email)

    @classmethod
    def register_lock(cls, email: str) -> str:
        return cls._make("register_lock", email)

    @classmethod
    def trip_failure(cls, user_id: str) -> str:
        return cls._make("trip_failure", user_id)

    @classmethod
    def trip_failure_lock(cls, user_id: str) -> str:
        return cls._make("trip_failure_lock", user_id)

    @classmethod
    def trip_success(cls, user_id: str) -> str:
        return cls._make("trip_success", user_id)

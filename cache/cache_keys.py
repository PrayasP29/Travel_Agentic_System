"""Centralized cache key generation helpers.

All keys are prefixed to avoid collisions. Usage:
    key = CacheKeys.flight("AC123", "2026-08-01")
"""


class CacheKeys:
    PREFIX = "tripplanner"

    @staticmethod
    def _make(namespace: str, *parts: str) -> str:
        return f"{CacheKeys.PREFIX}:{namespace}:{':'.join(parts)}"

    @classmethod
    def flight(cls, airline: str, date: str) -> str:
        return cls._make("flight", airline, date)

    @classmethod
    def hotel(cls, city: str, checkin: str, checkout: str) -> str:
        return cls._make("hotel", city, checkin, checkout)

    @classmethod
    def weather(cls, city: str, date: str) -> str:
        return cls._make("weather", city, date)

    @classmethod
    def local(cls, city: str, query: str) -> str:
        return cls._make("local", city, query)

    @classmethod
    def search(cls, query: str) -> str:
        return cls._make("search", query)

    @classmethod
    def trip(cls, trip_id: str) -> str:
        return cls._make("trip", trip_id)

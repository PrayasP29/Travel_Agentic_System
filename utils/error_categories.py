"""Centralized exception classification for user-friendly error messages.

Classifies exceptions by type and context, returning messages safe for end users.
Developer-facing logs remain untouched — this module only governs what reaches the client.
"""


_MESSAGES = {
    "groq_quota": (
        "The AI service is currently unavailable because its request limit "
        "has been reached. Please try again after some time."
    ),
    "groq_timeout": (
        "The AI service took too long to respond. "
        "Please try again in a few moments."
    ),
    "mcp_connection": (
        "Some travel services are currently unavailable. "
        "Please try again later."
    ),
    "flight": "We couldn't retrieve flight information at the moment.",
    "hotel": "We couldn't retrieve hotel information at the moment.",
    "weather": "We couldn't retrieve weather information at the moment.",
    "search": "We couldn't retrieve destination information at the moment.",
    "local": "We couldn't retrieve local recommendations at the moment.",
    "graph": (
        "We couldn't generate your travel itinerary because an internal "
        "error occurred. Please try again later."
    ),
    "unknown": (
        "Something went wrong while planning your trip. "
        "Please try again later."
    ),
}


def _is_rate_limit(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    return (
        "ratelimit" in name
        or ("rate" in name and "limit" in name)
        or "429" in msg
        or "rate limit" in msg
        or "quota" in msg
        or "too many requests" in msg
    )


def _is_timeout(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    return "timeout" in name or "timeout" in msg


def _is_connection(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    return (
        "connection" in name
        or "connection" in msg
        or "connect" in msg
        or "unavailable" in msg
    )


def classify_error(exc: BaseException, context: str = "") -> str:
    """Classify an exception and return a user-friendly message.

    Args:
        exc: The caught exception.
        context: Service context — one of "groq", "mcp", "flight", "hotel",
                 "weather", "search", "local", "graph", or "".

    Returns:
        A user-friendly error message string.
    """
    ctx = context.lower()

    if _is_rate_limit(exc) and ("groq" in ctx or not ctx):
        return _MESSAGES["groq_quota"]

    if _is_timeout(exc) and "groq" in ctx:
        return _MESSAGES["groq_timeout"]

    if ("mcp" in ctx or "weather_mcp" in ctx) and (
        _is_connection(exc) or _is_timeout(exc)
    ):
        return _MESSAGES["mcp_connection"]

    for key in ("flight", "hotel", "weather", "search", "local"):
        if key in ctx:
            return _MESSAGES[key]

    return _MESSAGES["unknown"]

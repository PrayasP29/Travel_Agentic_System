"""Shared utilities for the trip planner."""


def last_message_content(response) -> str:
    """Extract the final message content from a LangChain agent response.

    Handles dict responses with 'messages' key, string responses,
    objects with .messages attribute, and objects with .content attribute.
    """
    if response is None:
        return ""

    if isinstance(response, str):
        return response

    if isinstance(response, dict):
        messages = response.get("messages", [])
    else:
        messages = getattr(response, "messages", None)
        if messages is None and hasattr(response, "content"):
            return getattr(response, "content", "") or ""
        if messages is None:
            return str(response)

    if not messages:
        return ""

    last_message = messages[-1]
    if isinstance(last_message, dict):
        return last_message.get("content", "") or ""

    return getattr(last_message, "content", "") or str(last_message)

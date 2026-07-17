"""Groq model helpers for text generation."""

from langchain_groq import ChatGroq

from config.settings import settings


def get_text_llm() -> ChatGroq:
    """Create the LangChain chat model backed by Groq."""
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is required to initialize the text LLM.")

    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_text_model,
        temperature=0.2,
    )

"""Groq model helpers for text generation and audio transcription."""

from pathlib import Path
from typing import Union

from groq import APIError, Groq
from langchain_groq import ChatGroq

from config.settings import settings

AudioPath = Union[str, Path]


def get_text_llm() -> ChatGroq:
    """Create the LangChain chat model backed by Groq."""
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is required to initialize the text LLM.")

    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_text_model,
        temperature=0.2,
    )


def get_groq_client() -> Groq:
    """Create the native Groq client for APIs such as audio transcription."""
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is required to initialize the Groq client.")

    return Groq(api_key=settings.groq_api_key)


def transcribe_audio(audio_path: AudioPath) -> str:
    """Transcribe an audio file with Groq Whisper."""
    path = Path(audio_path)

    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    if not path.is_file():
        raise ValueError(f"Audio path must point to a file: {path}")

    client = get_groq_client()

    try:
        with path.open("rb") as audio_file:
            # Groq's transcription endpoint expects a binary file object.
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model=settings.groq_transcription_model,
            )
    except APIError as exc:
        raise RuntimeError(f"Groq transcription failed: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"Unable to read audio file '{path}': {exc}") from exc

    text = getattr(transcription, "text", None)
    if not text:
        raise RuntimeError("Groq transcription returned no text.")

    return text

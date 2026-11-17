"""API router defining health, metrics, examples, and chat endpoints."""

import os
from fastapi import APIRouter, Depends, Request
from src.chatbot import MovieAssistant
from .schemas import ChatRequest, ChatResponse, HealthResponse, MetricsResponse

router = APIRouter(prefix="/api", tags=["Assistant"])

EXAMPLE_QUERIES = [
    "movies like Inception",
    "recommend a comedy",
    "top rated movies",
    "movies similar to Interstellar",
    "recommend an action movie",
    "recommend based on The Matrix, Avatar",
]


def get_assistant(request: Request):
    """Retrieve shared assistant instance from app state, initializing if not present."""
    if not hasattr(request.app.state, "assistant") or request.app.state.assistant is None:
        api_key = os.getenv("TMDB_API_KEY", "").strip()
        request.app.state.assistant = MovieAssistant(api_key if api_key and api_key != "your_key_here" else None)
    return request.app.state.assistant


@router.get("/health", response_model=HealthResponse)
def health_check(request: Request) -> HealthResponse:
    """Check whether TMDB API is configured and service status."""
    assistant = get_assistant(request)
    configured = assistant.client.is_configured
    if configured:
        return HealthResponse(
            status="ok",
            tmdb_configured=True,
            message="TMDB API is configured and operational.",
        )
    return HealthResponse(
        status="degraded",
        tmdb_configured=False,
        message="TMDB_API_KEY is missing or invalid. Please configure your key in .env.",
    )


@router.get("/examples", response_model=list[str])
def get_examples() -> list[str]:
    """Provide suggested example queries for the user interface."""
    return EXAMPLE_QUERIES


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(request: Request) -> MetricsResponse:
    """Return runtime cache statistics and rate-limit estimates."""
    assistant = get_assistant(request)
    stats = assistant.client.get_metrics()
    return MetricsResponse(
        cache_size=stats["cache_size"],
        api_calls_today=stats["api_calls_today"],
        rate_limit_remaining=stats["rate_limit_remaining"],
    )


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest, request: Request) -> ChatResponse:
    """Chat endpoint to process user messages and return movie recommendations."""
    assistant = get_assistant(request)
    filters_dict = payload.filters.model_dump(exclude_none=True) if payload.filters else None
    result = assistant.reply(payload.message, filters=filters_dict)
    return ChatResponse(**result)


@router.post("/reset")
def reset_session(request: Request):
    """Reset recommendation session history and pagination."""
    assistant = get_assistant(request)
    assistant.seen_movie_ids.clear()
    assistant.last_query.clear()
    assistant.genre_pages.clear()
    assistant.language_pages.clear()
    assistant.top_rated_page = 1
    return {"status": "ok", "message": "Session reset"}

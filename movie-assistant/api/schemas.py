"""Pydantic schemas for request and response models."""

from typing import Optional
from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    """Schema for a movie recommendation item."""
    id: Optional[int] = None
    title: str
    year: str = ""
    genres: list[str] = Field(default_factory=list)
    rating: float = 0.0
    poster_url: Optional[str] = None
    reason: str = ""


class FilterOptions(BaseModel):
    """Optional filtering criteria for movie discovery."""
    genre: Optional[str] = None
    language: Optional[str] = None
    min_rating: Optional[float] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    sort_by: Optional[str] = "vote_average.desc"


class ChatRequest(BaseModel):
    """Schema for user chat input."""
    message: str = Field(..., min_length=1, max_length=500, description="User prompt text")
    filters: Optional[FilterOptions] = None


class ChatResponse(BaseModel):
    """Schema for chatbot response with structured recommendations."""
    reply: str
    recommendations: list[Recommendation] = Field(default_factory=list)
    intent: str


class HealthResponse(BaseModel):
    """Schema for API and TMDB health status."""
    status: str  # "ok" or "degraded"
    tmdb_configured: bool
    message: str


class MetricsResponse(BaseModel):
    """Schema for cache and rate limit metrics."""
    cache_size: int
    api_calls_today: int
    rate_limit_remaining: str

"""FastAPI application entry point for Movie Assistant."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from src.chatbot import MovieAssistant
from .routes import router as api_router

# Load environment variables from .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("movie_app")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events."""
    api_key = os.getenv("TMDB_API_KEY", "").strip()
    if not api_key or api_key == "your_key_here":
        logger.warning(
            "*** TMDB_API_KEY is missing or unconfigured in .env! "
            "Server is running in DEGRADED mode. Please set your TMDB API key to enable live recommendations. ***"
        )
        app.state.assistant = MovieAssistant(None)
    else:
        logger.info("TMDB_API_KEY found. Initializing MovieAssistant with live TMDB client.")
        app.state.assistant = MovieAssistant(api_key)

    yield
    logger.info("Shutting down Movie Assistant app.")


app = FastAPI(
    title="Movie Recommender AI",
    description="Live TMDB-powered Movie Recommendation Chatbot for College AI Lab",
    version="1.0.0",
    lifespan=lifespan,
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception processing %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "reply": "I'm having trouble reaching the movie database right now. Please try again in a moment.",
            "recommendations": [],
            "intent": "error",
            "detail": str(exc),
        },
    )

# Mount Static Files
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include API Router
app.include_router(api_router)


# Serve Frontend
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Silence browser favicon 404 requests."""
    return Response(status_code=204)


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve the single-page frontend application."""
    index_file = BASE_DIR / "templates" / "index.html"
    if not index_file.exists():
        return JSONResponse(
            status_code=404,
            content={"error": "templates/index.html not found"},
        )
    return FileResponse(index_file)

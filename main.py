"""
main.py — Application Entry Point
==================================
Bootstraps the FastAPI application, mounts route modules and the
frontend SPA, and registers global exception handlers.

Run locally:
    uvicorn main:app --reload

Run via Docker:
    docker-compose up -d --build
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from services.database import (
    logger,
    UserAlreadyExists,
    UserNotFoundError,
    MovieAlreadyExists,
)
from routers import auth, users, movies

# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CineWave — Movie Recommendation API",
    description="A RESTful API for tracking movies and generating AI-powered recommendations via TMDB.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Router Registration
# Each router is defined in its own module under `routers/` for separation
# of concerns.  Prefixes and tags are set inside each router file.
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(movies.router)

# ---------------------------------------------------------------------------
# Static Frontend (SPA)
# Served at /ui — the `html=True` flag makes FastAPI serve index.html for
# directory-level requests, enabling client-side routing.
# ---------------------------------------------------------------------------
app.mount("/ui", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/", include_in_schema=False)
def redirect_to_ui():
    """Redirect bare root requests to the web interface."""
    return RedirectResponse(url="/ui")


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------
# These handlers intercept domain-specific exceptions raised anywhere in the
# request lifecycle and convert them to well-structured JSON responses so the
# frontend never receives raw Python tracebacks.
# ---------------------------------------------------------------------------


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    """Return 422 with structured field-level validation errors."""
    logger.info(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(UserNotFoundError)
async def user_not_found_handler(request: Request, exc: UserNotFoundError):
    """Return 404 when a requested user does not exist in the database."""
    logger.warning(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=404, content={"detail": "User not found"})


@app.exception_handler(UserAlreadyExists)
async def user_exists_handler(request: Request, exc: UserAlreadyExists):
    """Return 409 when attempting to register a duplicate username."""
    logger.warning(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=409, content={"detail": "User already exists."})


@app.exception_handler(MovieAlreadyExists)
async def movie_exists_handler(request: Request, exc: MovieAlreadyExists):
    """Return 409 when the movie is already in the user's tracked list."""
    logger.warning(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=409, content={"detail": "Movie already exists"})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions — prevents stack traces from leaking to clients."""
    logger.exception(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

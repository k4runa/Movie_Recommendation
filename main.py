"""
main.py — Application Entry Point

Bootstraps the FastAPI application, mounts route modules and the
frontend SPA, and registers global exception handlers.

Run locally:
    uvicorn main:app --reload

Run via Docker:
    docker-compose up -d --build
"""

import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from services.database import (
    logger,
    UserAlreadyExists,
    UserNotFoundError,
    MovieAlreadyExists,
    MovieNotFoundError,
    ReservedUsernameError,
)
from services.deps import users_manager
from routers import auth, users, movies, ai
from sqlalchemy.exc import IntegrityError
from services.cache import cache_service
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
# ---------------------------------------------------------------------------
# Lifespan Management
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events.
    At startup, creates database tables and ensures that at least one
    admin account is seeded.
    """    
    logger.info("Application startup: Creating tables and seeding admin...")
    await users_manager.create_tables()
    await users_manager.ensure_admin_exists()  # type: ignore
    # Start background cache cleaner
    cache_task = asyncio.create_task(cache_service.clear_expired())
    yield
    cache_task.cancel()
    logger.info("Application shutdown.")




class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' https://api.themoviedb.org https://image.tmdb.org"
        return response

# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------
# Enable documentation only in DEBUG mode (Security hardening)
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

app = FastAPI(
    title="CineWave API",
    description="A production-ready, AI-powered movie recommendation system with advanced security hardening.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    openapi_url="/openapi.json" if DEBUG else None,
)

# Parse allowed origins from environment
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)

# ---------------------------------------------------------------------------
# Router Registration
# Each router is defined in its own module under `routers/` for separation
# of concerns.  Prefixes and tags are set inside each router file.
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(movies.router)
app.include_router(ai.router)

# ---------------------------------------------------------------------------
# Static Frontend (SPA)
# Served at /ui — the `html=True` flag makes FastAPI serve index.html for
# directory-level requests, enabling client-side routing.
# ---------------------------------------------------------------------------
app.mount("/ui", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/", include_in_schema=False)
async def redirect_to_ui():
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


@app.exception_handler(MovieNotFoundError)
async def movie_not_found_handler(request: Request, exc: MovieNotFoundError):
    """Return 404 when the movie is not found in the user's tracked list."""
    logger.warning(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=404, content={"detail": "Movie not found"})


@app.exception_handler(ReservedUsernameError)
async def reserved_username_handler(request: Request, exc: ReservedUsernameError):
    """Return 400 when attempting to register a restricted username."""
    logger.warning(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """
    Catch-all for DB constraint violations (like unique constraints triggered by race conditions).
    Converts 500 errors into 409 Conflicts to act as an idempotent-safe response.
    """
    logger.warning(f"Integrity Error (Race condition prevented): {request.method} {request.url} -> {exc}")
    return JSONResponse(
        status_code=409,
        content={"detail": "Resource already exists or constraint violated. Request safely ignored."},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions — prevents stack traces from leaking to clients."""
    logger.exception(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

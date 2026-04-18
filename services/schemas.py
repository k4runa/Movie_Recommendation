"""
services/schemas.py — Pydantic Models (Request / Response)

Defines all request validation schemas and response models used by
the API.  FastAPI uses these for:

    • Automatic request body parsing and validation.
    • Response serialization — fields NOT listed in the response model
      are stripped from the output, preventing sensitive data leaks
      (e.g. password hashes, IP addresses for non-admin routes).
    • Auto-generated OpenAPI / Swagger documentation.
"""

from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------


class UserScheme(BaseModel):
    """
    Schema for user registration requests.

    Validates:
        - Username must be >= 5 characters with no special characters.
        - Email must be a valid address (enforced by Pydantic's EmailStr).
        - Password is accepted as-is (hashed server-side before storage).
    """

    username:       str         =   Field(..., min_length=4, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    password:       str         =   Field(..., max_length=128)
    email:          EmailStr
    # Optional hardware metadata from JS
    device:         str | None  =   None
    os:             str | None  =   None
    machine:        str | None  =   None
    memory:         str | None  =   None

    @field_validator("username")
    @classmethod
    def is_valid_username(cls, v):
        if len(v) < 4:
            raise ValueError("Username must be longer than 4 characters.")
        forbidden               =   set("@-.!'?*)(/{}%+^&")
        if forbidden & set(v):
            raise ValueError("Username shouldn't have any special characters.")
        return v


class MovieScheme(BaseModel):
    query:      str | None  = Field(None, max_length=100)
    tmdb_id:    str | int   = 0


# ---------------------------------------------------------------------------
# Response Models
#
# These models act as whitelists — only the fields declared here are
# included in the JSON response.  This is how we prevent password hashes,
# raw IP addresses, and other sensitive columns from leaking to clients.
# ---------------------------------------------------------------------------


class UserResponse(BaseModel):
    """Public-safe representation of a user record."""

    id:         int
    username:   str
    email:      str
    device:     str | None = None
    os:         str | None = None
    country:    str | None = None
    city:       str | None = None
    created_at: str
    last_seen:  str | None = None
    ai_enabled: bool
    max_toasts: int


class MovieResponse(BaseModel):
    """Representation of a tracked movie."""

    id:             int
    tmdb_id:        int
    title:          str
    overview:       str | None = None
    genre_ids:      str
    status:         str
    vote_average:   str | None = None
    poster_url:     str | None = None
    release_date:   str | None = None


class WatchedMovieResponse(BaseModel):
    """Representation of a movie marked as 'Watched'."""

    id:         int
    title:      str
    status:     str
    watched_at: str


# ---------------------------------------------------------------------------
# Envelope Response Models
#
# API endpoints return responses wrapped in a standard envelope:
#   { "success": true, "data": { ... } }
# These models enforce that contract at the schema level.
# ---------------------------------------------------------------------------


class APIResponseUser(BaseModel):
    """Envelope for a single user record."""

    success:        bool
    data:           dict[str, UserResponse]


class APIResponseUsersList(BaseModel):
    """Envelope for a paginated list of users."""

    success:        bool
    data:           dict[str, List[UserResponse]]


class APIResponseWatchedMoviesList(BaseModel):
    """Envelope for a paginated list of tracked movies."""

    success:        bool
    data:           dict[str, List[MovieResponse]]

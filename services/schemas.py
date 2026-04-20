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
from typing import List


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
    password:       str         =   Field(..., min_length=8, max_length=128)
    email:          EmailStr
    # Optional hardware metadata from JS
    device:         str | None  =   Field(None, max_length=100)
    os:             str | None  =   Field(None, max_length=100)
    machine:        str | None  =   Field(None, max_length=100)
    memory:         str | None  =   Field(None, max_length=100)

    @field_validator("username")
    @classmethod
    def is_valid_username(cls, v):
        if len(v) < 4:
            raise ValueError("Username must be longer than 4 characters.")
        forbidden               =   set("@-.!'?*)(/{}%+^&")
        if forbidden & set(v):
            raise ValueError("Username shouldn't have any special characters.")
        return v

    @field_validator("password")
    @classmethod
    def is_strong_password(cls, v):
        """Enforce password complexity: >= 8 chars, 1 upper, 1 digit, 1 special."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        if not any(c in '!@#$%^&*()-_=+[]{}|;:,.<>?/~`' for c in v):
            raise ValueError("Password must contain at least one special character.")
        return v


class GoogleLoginRequest(BaseModel):
    """Schema for Google Login requests."""
    credential: str


class MovieScheme(BaseModel):
    query:      str | None  = Field(None, max_length=200)
    tmdb_id:    int         = Field(0, ge=0, le=999999999)


class MessageCreate(BaseModel):
    receiver_id:    int
    content:        str         = Field(..., min_length=1, max_length=1000)

class MessageUpdate(BaseModel):
    content:        str         = Field(..., min_length=1, max_length=1000)


class PrivacyUpdate(BaseModel):
    is_private:     bool


class ProfileUpdate(BaseModel):
    nickname:   str | None = Field(None, max_length=50)
    bio:        str | None = Field(None, max_length=500)
    gender:     str | None = Field(None, max_length=30)
    age:        int | None = Field(None, ge=13, le=120)
    location:   str | None = Field(None, max_length=100)


# ---------------------------------------------------------------------------
# Response Models
#
# These models act as whitelists — only the fields declared here are
# included in the JSON response.  This is how we prevent password hashes,
# raw IP addresses, and other sensitive columns from leaking to clients.
# ---------------------------------------------------------------------------


class UserResponse(BaseModel):
    """Public-safe representation of a user record. Sensitive fields (ip, machine, hostname, memory, device_name) are excluded."""

    id:         int
    username:   str
    nickname:   str | None = None
    email:      str
    avatar_url: str | None = None
    bio:        str | None = None
    gender:     str | None = None
    age:        int | None = None
    location:   str | None = None
    show_age:   bool = True
    show_gender: bool = True
    show_location: bool = True
    show_bio:    bool = True
    show_favorites: bool = True
    country:    str | None = None
    city:       str | None = None
    created_at: str
    last_seen:  str | None = None
    ai_enabled: bool
    max_toasts: int
    dm_notifications: bool
    muted_users: str | None = None
    is_private: bool


class UserMinimalResponse(BaseModel):
    """Safe representation for discovery."""
    id:         int
    username:   str
    nickname:   str | None = None
    avatar_url: str | None = None
    bio:        str | None = None
    last_seen:  str | None = None


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


class MessageResponse(BaseModel):
    id:             int
    sender_id:      int
    receiver_id:    int
    content:        str
    is_read:        bool
    is_edited:      bool = False
    edited_at:      str | None = None
    message_type:   str
    attachment_url: str | None = None
    created_at:     str

class ConversationResponse(BaseModel):
    participant:    UserMinimalResponse
    last_message:   MessageResponse | None = None
    unread_count:   int
    status:         str = "ACCEPTED"


class SimilarityResponse(BaseModel):
    target_user:    UserMinimalResponse
    score:          float
    reasons:        str | None = None


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

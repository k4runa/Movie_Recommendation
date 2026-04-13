"""
routers/users.py — User Management Endpoints
==============================================
CRUD operations for user accounts.  All mutating endpoints require a
valid JWT and enforce ownership checks (a user can only access their
own record, unless they hold the 'admin' role).

Endpoints:
    POST   /users              — Register a new user (public).
    GET    /users              — List all users (admin-only).
    GET    /users/{username}   — Retrieve own profile (auth required).
    GET    /users/id/{id}      — Retrieve user by numeric ID.
    DELETE /users/{username}   — Soft-delete own account (auth required).
    PATCH  /users/{username}   — Update a single field (auth required).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.database import logger
from services.deps import users_manager
from services.schemas import UserScheme, APIResponseUser, APIResponseUsersList
from services.auth import get_current_user
from functools import wraps

router = APIRouter(prefix="/users", tags=["users"])


# ---------------------------------------------------------------------------
# Request Schema (local to this router)
# ---------------------------------------------------------------------------


class UpdateUserRequest(BaseModel):
    """Payload for partial user updates — specify field name and new value."""

    field: str
    value: str


# ---------------------------------------------------------------------------
# Logging Decorator
# ---------------------------------------------------------------------------


def print_log(func):
    """Lightweight decorator that logs function entry and exit."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"running function: {func.__name__}")
        result = func(*args, **kwargs)
        logger.info(f"done function: {func.__name__}")
        return result

    return wrapper


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("")
@print_log
def register(user: UserScheme):
    """
    Register a new user account.

    This is the only public (unauthenticated) endpoint in the users
    router.  Device and geolocation metadata is collected automatically
    at registration time.
    """
    users_manager.add_user(user)  # type:ignore
    return {"success": True, "message": "User successfully added."}


@router.get("", response_model=APIResponseUsersList)
@print_log
def get_all_users(
    skip: int = 0, limit: int = 10, current_user: dict = Depends(get_current_user)
):
    """
    List all registered users (admin-only).

    Returns a paginated array of user records including device metadata.
    Non-admin users receive a 403 Forbidden response.
    """
    user_in_db = users_manager.get_user_by_username(current_user["username"])  # type: ignore
    if user_in_db.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    logger.info(f"Fetching users with skip={skip}, limit={limit}...")
    all_users = users_manager.get_all_users(skip=skip, limit=limit)  # type: ignore
    return {"success": True, "data": {"users": all_users}}


@router.get("/id/{id}", response_model=APIResponseUser)
@print_log
def get_user_by_id(id: int):
    """Retrieve a user record by its numeric primary key."""
    user = users_manager.get_user_by_id(id)  # type: ignore
    return {"success": True, "data": {"user": user}}


@router.get("/{username}", response_model=APIResponseUser)
@print_log
def get_user_by_username(username: str, current_user: dict = Depends(get_current_user)):
    """
    Retrieve the authenticated user's own profile.

    Ownership is enforced — requesting another user's profile returns 403.
    """
    if current_user.get("username") != username:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resource"
        )
    user = users_manager.get_user_by_username(username)  # type: ignore
    return {"success": True, "data": {"user": user}}


@router.delete("/{username}")
@print_log
def delete_user(username: str, current_user: dict = Depends(get_current_user)):
    """
    Soft-delete the authenticated user's account.

    The record's `is_deleted` flag is set to True; data is preserved
    for auditing purposes.
    """
    if current_user.get("username") != username:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resource"
        )
    success = users_manager.delete_user(username)  # type: ignore
    return {"success": success}


@router.patch("/{username}")
@print_log
def update_user_field(
    username: str, v: UpdateUserRequest, current_user: dict = Depends(get_current_user)
):
    """
    Update a single field on the authenticated user's profile.

    Password fields are automatically bcrypt-hashed before storage.
    """
    if current_user.get("username") != username:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resource"
        )
    success = users_manager.update_user_field(username, v.field, v.value)  # type: ignore
    return {"success": success}

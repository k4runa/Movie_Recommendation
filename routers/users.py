"""
routers/users.py — User Management Endpoints

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

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from services.database import logger
from services.deps import users_manager
from services.schemas import UserScheme, APIResponseUser, APIResponseUsersList
from services.auth import get_current_user, create_access_token

router = APIRouter(prefix="/users", tags=["users"])


# ---------------------------------------------------------------------------
# Request Schema (local to this router)
# ---------------------------------------------------------------------------


class UpdateUserRequest(BaseModel):
    """Payload for partial user updates — specify field name and new value."""

    field: str
    value: str
    current_password: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("")
async def register(user: UserScheme, request: Request):
    """
    Register a new user account.

    Automatically collects device (User-Agent) and network (IP) metadata
    from the request headers for security and analytics.
    """
    # Extract metadata from headers
    user_agent = request.headers.get("User-Agent", "Unknown")
    
    # Capture real IP, considering proxies like Render's load balancer
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "127.0.0.1"
    
    await users_manager.add_user(user, user_agent=user_agent, ip=ip) # type:ignore
    return {"success": True, "message": "User successfully added."}


@router.get("", response_model=APIResponseUsersList)
async def get_all_users(
    skip: int = 0, limit: int = 10, current_user: dict = Depends(get_current_user)
):
    """
    List all registered users (admin-only).

    Returns a paginated array of user records including device metadata.
    Non-admin users receive a 403 Forbidden response.
    """
    user_in_db = await users_manager.get_user_by_username(current_user["username"])  # type: ignore
    if user_in_db.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    logger.info(f"Fetching users with skip={skip}, limit={limit}...")
    all_users = await users_manager.get_all_users(skip=skip, limit=limit)  # type: ignore
    return {"success": True, "data": {"users": all_users}}


@router.get("/id/{id}", response_model=APIResponseUser)
async def get_user_by_id(id: int, current_user: dict = Depends(get_current_user)):
    """
    Retrieve a user record by its numeric primary key (admin-only).
    """
    user_in_db = await users_manager.get_user_by_username(current_user["username"])  # type: ignore
    if user_in_db.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    user = await users_manager.get_user_by_id(id)  # type: ignore
    return {"success": True, "data": {"user": user}}


@router.get("/{username}", response_model=APIResponseUser)
async def get_user_by_username(
    username: str, current_user: dict = Depends(get_current_user)
):
    """
    Retrieve the authenticated user's own profile.

    Ownership is enforced — requesting another user's profile returns 403.
    """
    if current_user.get("username") != username:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resource"
        )
    user = await users_manager.get_user_by_username(username)  # type: ignore
    return {"success": True, "data": {"user": user}}


@router.delete("/{username}")
async def delete_user(username: str, current_user: dict = Depends(get_current_user)):
    """
    Soft-delete the authenticated user's account.

    The record's `is_deleted` flag is set to True; data is preserved
    for auditing purposes.
    """
    if current_user.get("username") != username:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resource"
        )
    success = await users_manager.delete_user(username)  # type: ignore
    return {"success": success}


@router.patch("/{username}")
async def update_user_field(
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
    try:
        success = await users_manager.update_user_field(
            username, v.field, v.value, v.current_password
        )  # type: ignore
        
        response = {"success": success}
        
        # If username changed, we must issue a new token
        if v.field.lower() == "username" and success:
            new_token = create_access_token(data={"sub": v.value})
            response["new_token"] = new_token
            response["new_username"] = v.value
            
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

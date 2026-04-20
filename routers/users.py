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

from fastapi import APIRouter, Depends, HTTPException, Request, File, UploadFile, Body, Response
import os
from pydantic import BaseModel
from services.database import logger
from services.schemas import UserScheme, APIResponseUser, APIResponseUsersList, ProfileUpdate
from services.deps import users_manager, limiter
from services.auth import get_current_user, create_access_token, get_token_from_cookie_or_header, blacklist_token, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
import jwt
from datetime import datetime, timezone

router = APIRouter(prefix="/users", tags=["users"])

async def _revoke_token(token: str):
    """Helper to blacklist a token until it naturally expires."""
    try:
        if not SECRET_KEY:
            return
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"require": ["exp"]})
        exp = payload.get("exp")
        if exp:
            now = datetime.now(timezone.utc).timestamp()
            ttl = int(exp - now)
            if ttl > 0:
                await blacklist_token(token, expires_in_seconds=ttl)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Request Schema (local to this router)
# ---------------------------------------------------------------------------


from typing import Any
from pydantic import Field as PydanticField

class UpdateUserRequest(BaseModel):
    """Payload for partial user updates — specify field name and new value."""

    field: str = PydanticField(..., max_length=50)
    value: Any
    current_password: str | None = PydanticField(None, max_length=128)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("")
@limiter.limit("5/minute")
async def register(response: Response, request: Request, user: UserScheme):
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
    
    # Fix 8.1: Set cookie on registration
    access_token = create_access_token(data={"sub": user.username})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return {"success": True, "message": "User successfully added.", "access_token": access_token}


@router.get("", response_model=APIResponseUsersList)
async def get_all_users(skip: int = 0, limit: int = 10, current_user: dict = Depends(get_current_user)):
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


@router.get("/me", response_model=APIResponseUser)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """
    Retrieve the authenticated user's own profile using their token.
    """
    user = await users_manager.get_user_by_username(current_user["username"]) #type: ignore
    return {"success": True, "data": {"user": user}}


@router.delete("/")
async def delete_user(response: Response, current_user: dict = Depends(get_current_user), token: str = Depends(get_token_from_cookie_or_header)):
    """
    Soft-delete the authenticated user's account.
    """
    username = current_user["username"]
    success = await users_manager.delete_user(username)  # type: ignore
    if success:
        await _revoke_token(token)
        response.delete_cookie(key="access_token", httponly=True, samesite="lax")
    return {"success": success}


@router.patch("/")
async def update_user_field(response: Response, v: UpdateUserRequest, current_user: dict = Depends(get_current_user), token: str = Depends(get_token_from_cookie_or_header)):
    """
    Update a single field on the authenticated user's profile.
    """
    username = current_user["username"]
    try:
        success = await users_manager.update_user_field(username, v.field, v.value, v.current_password)  # type: ignore
        
        # If username changed, we must issue a new token and revoke the old one
        if v.field.lower() == "username" and success:
            await _revoke_token(token)
            new_token = create_access_token(data={"sub": v.value})
            
            response.set_cookie(
                key="access_token",
                value=new_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
            
            response_data = {"success": str(success)}
            response_data["new_token"] = new_token
            response_data["new_username"] = v.value
            return response_data

        # If password changed, revoke the old token and clear cookie
        elif v.field.lower() == "password" and success:
            await _revoke_token(token)
            response.delete_cookie(key="access_token", httponly=True, samesite="lax")
            
        return {"success": str(success)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/profile")
async def update_user_profile(profile_data: ProfileUpdate = Body(...), current_user: dict = Depends(get_current_user)):
    """
    Update multiple profile fields (bio, age, gender, location) at once.
    """
    username = current_user["username"]
    # Filter out None values
    update_dict = {k: v for k, v in profile_data.model_dump().items() if v is not None} 
    success = await users_manager.update_profile(username, update_dict) #type: ignore
    return {"success": success}

ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_AVATAR_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2 MB

@router.post("/avatar")
@limiter.limit("5/minute")
async def upload_avatar(request: Request,file: UploadFile = File(...),current_user: dict = Depends(get_current_user)):
    """
    Upload a profile picture for the authenticated user.
    Saves the file locally and updates the avatar_url in the database.
    """
    # Validate MIME type
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(status_code=400, detail=f"File must be an image ({', '.join(ALLOWED_AVATAR_EXTS)}).")

    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".jpg"
    if ext not in ALLOWED_AVATAR_EXTS:
        raise HTTPException(status_code=400, detail=f"Invalid file extension. Allowed: {', '.join(ALLOWED_AVATAR_EXTS)}")

    # Enforce file size server-side (read up to limit + 1 byte to detect oversize)
    contents = await file.read(MAX_AVATAR_BYTES + 1)
    if len(contents) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=400, detail="Avatar file must be under 2 MB.")

    filename = f"{current_user['username']}_{int(datetime.now().timestamp())}{ext}"
    file_path = os.path.join("uploads", filename)

    try:
        os.makedirs("uploads", exist_ok=True)
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        
        avatar_url = f"/uploads/{filename}"
        await users_manager.update_user_field(current_user["username"], "avatar_url", avatar_url)   #type: ignore
        
        return {"success": True, "avatar_url": avatar_url}
    except Exception as e:
        logger.error(f"Avatar upload failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Could not save avatar.")

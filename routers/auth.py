"""
routers/auth.py — Authentication Endpoints

Handles user login via OAuth2-compatible form submission.

Endpoints:
    POST /login  — Authenticate with username + password, receive a JWT.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from services.auth import verify_password, create_access_token, oauth2_scheme
from services.database import UserNotFoundError
from services.deps import users_manager

router = APIRouter(tags=["auth"])


import bcrypt

# Pre-computed dummy hash to prevent timing attacks
DUMMY_HASH = bcrypt.hashpw(b"dummy_password", bcrypt.gensalt()).decode("utf-8")


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate a user and return a JWT access token.

    Accepts OAuth2-standard form fields (`username`, `password`).
    On success, returns `{ access_token, token_type }`.

    Raises:
        HTTPException 401: If the username doesn't exist or the password
                           is incorrect.  The error message is intentionally
                           vague to prevent user enumeration.
    """
    user_in_db = None
    try:
        user_in_db = await users_manager.get_user_by_username(form_data.username)  # type: ignore
    except UserNotFoundError:
        pass

    # Normalize response time to prevent User Enumeration via Timing Attacks
    hashed = user_in_db.get("password", "") if user_in_db else DUMMY_HASH
    is_valid = await verify_password(form_data.password, hashed)

    if not user_in_db or not is_valid:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": user_in_db["username"]})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user_in_db["username"],
        "role": user_in_db["role"],
    }


@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """
    Invalidate the current user's token by adding it to the server-side blacklist.
    """
    from services.auth import blacklist_token, SECRET_KEY, ALGORITHM, oauth2_scheme
    import jwt
    from datetime import datetime, timezone

    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM], options={"require": ["exp"]}
        )
        exp = payload.get("exp")
        if exp:
            now = datetime.now(timezone.utc).timestamp()
            ttl = int(exp - now)
            if ttl > 0:
                await blacklist_token(token, expires_in_seconds=ttl)
    except Exception:
        # If token is invalid or expired, it's essentially already logged out
        pass

    return {"success": True, "message": "Successfully logged out"}

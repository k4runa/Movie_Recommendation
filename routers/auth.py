"""
routers/auth.py — Authentication Endpoints

Handles user login via OAuth2-compatible form submission.

Endpoints:
    POST /login  — Authenticate with username + password, receive a JWT.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from services.auth import verify_password, create_access_token, oauth2_scheme
from services.database import UserNotFoundError
from services.deps import users_manager, limiter
import bcrypt
from services.auth import blacklist_token, SECRET_KEY, ALGORITHM, oauth2_scheme, verify_google_token
from services.schemas import GoogleLoginRequest
import jwt
from datetime import datetime, timezone


router = APIRouter(tags=["auth"])

# Pre-computed dummy hash to prevent timing attacks
DUMMY_HASH = bcrypt.hashpw(b"dummy_password", bcrypt.gensalt()).decode("utf-8")


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate a user and return a JWT access token.

    Accepts OAuth2-standard form fields (`username`, `password`).
    On success, returns `{ access_token, token_type }`.

    Raises:
        HTTPException 401: If the username doesn't exist or the password
                           is incorrect.  The error message is intentionally
                           vague to prevent user enumeration.
    """
    user_in_db              =   None
    try:
        user_in_db          =   await users_manager.get_user_by_username(form_data.username)  # type: ignore
    except UserNotFoundError:
        pass

    # Normalize response time to prevent User Enumeration via Timing Attacks
    hashed                  =   user_in_db.get("password", "") if user_in_db else DUMMY_HASH
    is_valid                =   await verify_password(form_data.password, hashed)

    if not user_in_db or not is_valid:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token            =   create_access_token(data={"sub": user_in_db["username"]})
    
    return {"access_token": access_token,"token_type": "bearer","username": user_in_db["username"],"role": user_in_db["role"],}


@router.post("/google-login")
async def google_login(request: Request, body: GoogleLoginRequest):
    """
    Authenticate a user via Google OAuth2.
    """
    idinfo = await verify_google_token(body.credential)
    
    if not idinfo:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    
    email = idinfo.get("email")
    name = idinfo.get("name", "Google User")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by Google")
    
    # Get or create user in DB
    user_in_db = await users_manager.get_or_create_google_user(
        email=email,
        name=name,
        ip=request.client.host if request.client else "Unknown",
        user_agent=request.headers.get("user-agent", "Unknown")
    )
    
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
    try:
        if SECRET_KEY:
            payload         =   jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"require": ["exp"]})
            exp             =   payload.get("exp")
            if exp:
                now         =   datetime.now(timezone.utc).timestamp()
                ttl         =   int(exp - now)
                
                if ttl > 0:
                    await blacklist_token(token, expires_in_seconds=ttl)
        else:
            print(f"ERROR: SECRET_KEY IS NOT SET. PLEASE SET IN '.env'")
            return 
    except Exception:
        # If token is invalid or expired, it's essentially already logged out
        pass

    return {"success": True, "message": "Successfully logged out"}

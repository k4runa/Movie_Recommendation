"""
services/auth.py — Authentication & Authorization

Implements JWT-based authentication for the API.

Flow:
    1. User submits credentials to POST /login.
    2. `verify_password` checks the plaintext against the bcrypt hash.
    3. `create_access_token` mints a signed JWT with an expiry claim.
    4. Protected routes use `get_current_user` (an injectable FastAPI
       dependency) to decode and validate the Bearer token on every request.

Environment variables (loaded from .env):
    JWT_SECRET_KEY              — HMAC signing key (REQUIRED).
    JWT_ALGORITHM               — Algorithm, defaults to HS256.
    ACCESS_TOKEN_EXPIRE_MINUTES — Token TTL in minutes, defaults to 120.
"""

import httpx
import os
import bcrypt
import logging
import jwt
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, status, Depends, Request
from starlette.concurrency import run_in_threadpool
from dotenv import load_dotenv
from services.cache import cache_service

load_dotenv()
logger                          =   logging.getLogger(__name__)

# Google Auth Imports
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# ---------------------------------------------------------------------------
# Configuration — sourced from environment variables
# ---------------------------------------------------------------------------
SECRET_KEY                      =   os.getenv("JWT_SECRET_KEY")
ALGORITHM                       =   "HS256" # Hardcoded for security
ACCESS_TOKEN_EXPIRE_MINUTES     =   int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
GOOGLE_CLIENT_ID                =   os.getenv("GOOGLE_CLIENT_ID")

# FastAPI's OAuth2 scheme — extracts the Bearer token from the
# Authorization header if cookie is missing.
oauth2_scheme                   =   OAuth2PasswordBearer(tokenUrl = "login", auto_error=False)

def get_token_from_cookie_or_header(request: Request, header_token: str | None = Depends(oauth2_scheme)) -> str:
    """Extracts token from httpOnly cookie 'access_token' or fallback to Authorization header."""
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    if header_token:
        return header_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

# ---------------------------------------------------------------------------
# Google Auth Verification
# ---------------------------------------------------------------------------
async def verify_google_token(token: str) -> dict | None:
    """
    Verifies a Google token. It first tries to verify it as an ID Token,
    and if that fails, it tries to fetch user info via Access Token.
    """
    if not GOOGLE_CLIENT_ID:
        logger.error(f"GOOGLE_CLIENT_ID not found.")
        return None
    try:
        idinfo = await run_in_threadpool(id_token.verify_oauth2_token,token,google_requests.Request(),GOOGLE_CLIENT_ID)
        if idinfo["aud"] != GOOGLE_CLIENT_ID:
            return None
        return idinfo   #type: ignore
    except Exception as exc:
        logger.warning(f"ID token verification failed - error: {str(exc)}")

    try:
        async with httpx.AsyncClient(timeout=0.5) as client:
            response = await client.get("https://oauth2.googleapis.com/tokeninfo",params={"access_token": token})
            if response.status_code == 200:
                data = response.json()
                if data.get("aut") != GOOGLE_CLIENT_ID:
                    return None
                return data
    except Exception as exc:
        logger.error(f"Access token verification failed - error: {str(exc)}")

    return None
# ---------------------------------------------------------------------------
# Token Blacklisting
# ---------------------------------------------------------------------------
async def is_token_blacklisted(token: str) -> bool:
    """Check if the token has been revoked."""
    val             =   await cache_service.get(f"bl_{token}")
    return val is not None

async def blacklist_token(token: str, expires_in_seconds: int):
    """Add a token to the blacklist until it naturally expires."""
    logger.info(f"Revoking token (Fix 2.2): expires in {expires_in_seconds}s")
    await cache_service.set(f"bl_{token}", "revoked", ttl = expires_in_seconds)


# ---------------------------------------------------------------------------
# Password Utilities
# ---------------------------------------------------------------------------


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compare a plaintext password against a bcrypt hash asynchronously.
    """
    try:
        if isinstance(plain_password, str):
            plain_password          =   plain_password.encode("utf-8") #type: ignore
        if isinstance(hashed_password, str):
            hashed_password         =   hashed_password.encode("utf-8") #type: ignore

        # Run the blocking bcrypt call in a thread pool
        return await run_in_threadpool(bcrypt.checkpw, plain_password, hashed_password) #type: ignore
    except Exception as e:
        logger.error(f"Error checking password: {e}")
        return False


# ---------------------------------------------------------------------------
# Token Creation
# ---------------------------------------------------------------------------


def create_access_token(data: dict):
    """
    Mint a new JWT access token.

    Args:
        data: Claims to encode (must include 'sub' for the username).

    Returns:
        Encoded JWT string.

    Raises:
        ValueError: If JWT_SECRET_KEY is not set in the environment.
    """
    if not SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY not found in environment variables.")

    to_encode           =   data.copy()
    expire              =   datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt         =   jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ---------------------------------------------------------------------------
# FastAPI Dependency — Token Validation
# ---------------------------------------------------------------------------


async def get_current_user(token: str = Depends(get_token_from_cookie_or_header)):
    """
    Decode and validate a Bearer token, returning the authenticated user's
    identity as a dict.

    This function is designed to be used as a FastAPI `Depends()` injection.
    Protected routes simply declare `current_user: dict = Depends(get_current_user)`
    to enforce authentication.

    Returns:
        dict with key 'username' extracted from the token's 'sub' claim.

    Raises:
        HTTPException 401: On missing, expired, tampered tokens, or deleted users.
    """
    from services.deps import users_manager
    from services.database import UserNotFoundError

    credentials_exception           =   HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Could not validate credentials",headers={"WWW-Authenticate": "Bearer"},)

    if not SECRET_KEY:
        logger.error("SECRET_KEY missing when trying to validate token.")
        raise credentials_exception

    try:
        if await is_token_blacklisted(token):
            logger.warning("Attempted use of blacklisted token.")
            raise credentials_exception

        payload                     =   jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"require": ["exp"]})
        username:str                =   payload.get("sub")  # type: ignore
        if username:
            try:
                user_in_db = await users_manager.get_user_by_username(username) #type: ignore
                if user_in_db.get("is_deleted"):
                    logger.warning(f"Attempted access by deleted user: {username}")
                    raise credentials_exception
                
                # Update last_seen asynchronously
                await users_manager.update_last_seen(username)  #type: ignore
            except UserNotFoundError:
                logger.warning(f"Attempted access by non-existent user: {username}")
                raise credentials_exception

            token_data = {
                "username": username,
                "id": user_in_db.get("id"),
                "role": user_in_db.get("role", "user")
            }
            return token_data
        raise credentials_exception
    except jwt.ExpiredSignatureError:
        logger.warning(f"Token expired for user validation.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Token has expired. Please login again.",headers={"WWW-Authenticate": "Bearer"},)
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise credentials_exception

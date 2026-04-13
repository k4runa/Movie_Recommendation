"""
services/auth.py — Authentication & Authorization
===================================================
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

import os
import bcrypt
import logging
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — sourced from environment variables
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

# FastAPI's OAuth2 scheme — extracts the Bearer token from the
# Authorization header and feeds it to `get_current_user`.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# ---------------------------------------------------------------------------
# Password Utilities
# ---------------------------------------------------------------------------


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compare a plaintext password against a bcrypt hash.

    Handles the str → bytes conversion internally so callers don't
    have to worry about encoding.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        if isinstance(plain_password, str):
            plain_password = plain_password.encode("utf-8")
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode("utf-8")

        return bcrypt.checkpw(plain_password, hashed_password)
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

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ---------------------------------------------------------------------------
# FastAPI Dependency — Token Validation
# ---------------------------------------------------------------------------


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Decode and validate a Bearer token, returning the authenticated user's
    identity as a dict.

    This function is designed to be used as a FastAPI `Depends()` injection.
    Protected routes simply declare `current_user: dict = Depends(get_current_user)`
    to enforce authentication.

    Returns:
        dict with key 'username' extracted from the token's 'sub' claim.

    Raises:
        HTTPException 401: On missing, expired, or tampered tokens.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not SECRET_KEY:
        logger.error("SECRET_KEY missing when trying to validate token.")
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        token_data = {"username": username}
        return token_data

    except jwt.ExpiredSignatureError:
        logger.warning(f"Token expired for user validation.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise credentials_exception

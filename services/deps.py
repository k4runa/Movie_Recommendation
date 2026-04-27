"""
services/deps.py — Dependency Injection (Singleton Managers)

Creates singleton instances of UserManager and MovieManager that are
shared across all request handlers via Python module-level imports.

The database URL is read from the DATABASE_URL environment variable,
which should be a PostgreSQL asyncpg connection string.

Usage in routers:
    from services.deps import users_manager, movies_manager
"""

import os
from .database import UserManager, MovieManager, SocialManager, AIManager, NotificationManager, TokenManager, init_database
from dotenv import load_dotenv
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

logger = logging.getLogger(__name__)
load_dotenv()

# Initialize global rate limiter
# Use X-Forwarded-For when behind a reverse proxy (Render, Nginx), fallback to remote address.
def _get_real_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first (client) IP, ignore proxy chain
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)

import sys
is_testing = "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST") is not None
limiter = Limiter(key_func=_get_real_ip, enabled=not is_testing)

# ---------------------------------------------------------------------------
# Database URL Resolution
# ---------------------------------------------------------------------------
def get_sanitized_url(env_key: str, driver: str) -> str:
    url = os.getenv(env_key)  
    if not url:
        return ""
    # Render and others provide postgres://, but SQLAlchemy needs postgresql+driver://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", f"postgresql+{driver}://", 1)
    elif url.startswith("postgresql://") and f"+{driver}" not in url:
        url = url.replace("postgresql://", f"postgresql+{driver}://", 1)    
    return url
DATABASE_URL = get_sanitized_url("DATABASE_URL", "asyncpg")

if not DATABASE_URL:
    logger.error("FATAL: DATABASE_URL not found.")
    raise ValueError("FATAL: DATABASE_URL not found. Please set in .env")

# ---------------------------------------------------------------------------
# Initialize Shared Engine
# ---------------------------------------------------------------------------
init_database(DATABASE_URL)

# ---------------------------------------------------------------------------
# Singleton Manager Instances
# ---------------------------------------------------------------------------
# These are instantiated once at import time and reused for the lifetime
# of the process. They share the same underlying engine and session pool.
# ---------------------------------------------------------------------------
users_manager = UserManager()
movies_manager = MovieManager()
social_manager = SocialManager()
ai_manager = AIManager()
notification_manager = NotificationManager()
token_manager = TokenManager()

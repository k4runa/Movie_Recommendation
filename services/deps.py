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
from services.database import UserManager, MovieManager
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)
load_dotenv()

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
# Singleton Manager Instances
# ---------------------------------------------------------------------------
# These are instantiated once at import time and reused for the lifetime
# of the process.  Each manager creates its own async engine and session factory.
# ---------------------------------------------------------------------------
users_manager = UserManager(db_url=DATABASE_URL, echo=False)
movies_manager = MovieManager(db_url=DATABASE_URL, echo=False)

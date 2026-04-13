"""
services/deps.py — Dependency Injection (Singleton Managers)
=============================================================
Creates singleton instances of UserManager and MovieManager that are
shared across all request handlers via Python module-level imports.

The database path is read from the DB_PATH environment variable.
If the parent directory does not exist, it is created automatically
so the SQLite file can be initialized on first run.

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
# Database Path Resolution
# ---------------------------------------------------------------------------
DB_PATH = os.getenv("DB_PATH", "database/database.db")
if not DB_PATH:
    logger.error("FATAL: DB_PATH not found.")
    raise ValueError("FATAL: DB_PATH not found. Please set in .env")

# Ensure the directory tree exists before SQLAlchemy tries to create the file
dir_path = os.path.dirname(DB_PATH)
if dir_path:
    os.makedirs(dir_path, exist_ok=True)

# ---------------------------------------------------------------------------
# Singleton Manager Instances
# ---------------------------------------------------------------------------
# These are instantiated once at import time and reused for the lifetime
# of the process.  Each manager creates its own engine and session factory.
# ---------------------------------------------------------------------------
users_manager = UserManager(db_path=DB_PATH, echo=False)  # type:ignore
movies_manager = MovieManager(db_path=DB_PATH, echo=False)  # type:ignore

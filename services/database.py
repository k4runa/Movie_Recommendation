"""
services/database.py — Async Data Access Layer (PostgreSQL)

Defines the SQLAlchemy ORM models (User, Movies, WatchedMovies) and the
manager classes (UserManager, MovieManager) that encapsulate all database
operations behind clean, transactional interfaces.

Design decisions:
    • PostgreSQL via asyncpg is used as the primary datastore.
    • The async engine URL is injected via the DATABASE_URL environment variable.
    • Every write operation is wrapped in an auto-commit / rollback
      async transaction decorator so callers never manage sessions directly.
    • Device and network metadata is collected at registration time for
      analytics purposes — this is intentional.
"""

from services.tmdb import fetch_tmdb_data, fetch_tmdb_movie_by_id
from sqlalchemy import (
    ForeignKey,
    String,
    Integer,
    Boolean,
    JSON,
    select,
    delete,
    update,
    or_,
    and_,
    func,
    UniqueConstraint,
    Index,
)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from fastapi.concurrency import run_in_threadpool
from functools import wraps
from typing import List, Optional, Any
import os
import logging
import bcrypt
import secrets
import uuid
from datetime import datetime, timezone
from collections import Counter
from dotenv import load_dotenv
from .schemas import UserScheme, MovieScheme

# ---------------------------------------------------------------------------
# Global Constants
# ---------------------------------------------------------------------------

RESERVED_USERNAMES = {"admin", "root", "system", "superuser", "administrator"}
load_dotenv()

db_url = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://ecofil:[EMAIL_ADDRESS]:5432/ecofil_db"
)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://") and "asyncpg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
os.environ["DATABASE_URL"] = db_url

db_url_sync = os.getenv("DATABASE_URL_SYNC", "sqlite:///./database/ecofil.db")
if db_url_sync.startswith("postgres://"):
    db_url_sync = db_url_sync.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url_sync.startswith("postgresql://") and "psycopg2" not in db_url_sync:
    db_url_sync = db_url_sync.replace("postgresql://", "postgresql+psycopg2://", 1)
os.environ["DATABASE_URL_SYNC"] = db_url_sync
 
SENSITIVE_FIELDS = {"password", "ip", "hostname", "device_name", "machine", "memory", "device", "os"}

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
format = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=format)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQLAlchemy Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""
    pass

# ---------------------------------------------------------------------------
# Database Configuration & Shared Engine
# ---------------------------------------------------------------------------
# We define a single engine and session factory to be shared across all
# managers. This is critical for performance and memory management.
# ---------------------------------------------------------------------------
_engine        = None
_session_maker = None


def init_database(db_url: str, echo: bool = False):
    """Initialize the global engine and session maker."""
    global _engine, _session_maker
    import sys
    from sqlalchemy.pool import NullPool

    # Use NullPool during testing, otherwise use QueuePool with tight limits
    if "pytest" in sys.modules:
        poolclass = NullPool
        _engine = create_async_engine(db_url, echo=echo, poolclass=poolclass)
    else:
        _engine = create_async_engine(db_url,echo=echo,pool_size=5,max_overflow=10,pool_recycle=1800,pool_pre_ping=True)
    _session_maker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Custom Domain Exceptions
# ---------------------------------------------------------------------------
# These are raised by manager methods and caught by the FastAPI exception
# handlers in main.py to produce structured JSON error responses.
# ---------------------------------------------------------------------------


class UserAlreadyExists(Exception):
    """Raised when attempting to register a username that is already taken."""

    def __init__(self, username: str, *args: object) -> None:
        super().__init__(f"User {username} already exists - args=({args})")

class ReservedUsernameError(Exception):
    """Raised when attempting to register a restricted username (e.g. admin)."""

    def __init__(self, username: str, *args: object) -> None:
        super().__init__(f"Username {username} is reserved and cannot be registered - args=({args})")


class UserNotFoundError(Exception):
    """Raised when a database lookup for a user yields no results."""

    def __init__(self, username: str, *args: object) -> None:
        super().__init__(f"User {username} not found - args=({args})")

class MovieAlreadyExists(Exception):
    """Raised when a movie is already in the user's tracked collection."""

    def __init__(self, title: str, *args: object) -> None:
        super().__init__(f"Movie {title} already exists - args=({args})")

class MovieNotFoundError(Exception):
    """Raised when a movie is not found in the user's tracked collection."""

    def __init__(self, title: str, *args: object) -> None:
        super().__init__(f"Movie {title} not found - args=({args})")


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------


class User(Base):
    """
    Represents a registered user in the system.

    Beyond standard auth fields (username, password, email), this model
    stores device fingerprint and geolocation metadata collected at
    registration time.  The `role` column controls access to admin
    features ('admin' vs 'user').

    Relationships:
        movies — one-to-many link to the Movies table (tracked films).
    """

    __tablename__                                                   =   "users"

    id:                             Mapped[int]                     =   mapped_column(primary_key=True)
    username:                       Mapped[str]                     =   mapped_column(String, unique=True, nullable=False)
    nickname:                       Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    full_name:                      Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    role:                           Mapped[str]                     =   mapped_column(String, nullable=False, default="user", server_default="user")
    password:                       Mapped[str]                     =   mapped_column(String, nullable=False)
    email:                          Mapped[str]                     =   mapped_column(String, unique=True, nullable=False)
    avatar_url:                     Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    bio:                            Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    social_links:                   Mapped[Optional[dict]]          =   mapped_column(JSON, nullable=True)
    favorite_genres:                Mapped[Optional[List[int]]]     =   mapped_column(JSON, nullable=True)
    gender:                         Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    age:                            Mapped[Optional[int]]           =   mapped_column(Integer, nullable=True)
    location:                       Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    social_link:                    Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    show_age:                       Mapped[bool]                    =   mapped_column(Boolean, default=True)
    show_gender:                    Mapped[bool]                    =   mapped_column(Boolean, default=True)
    show_location:                  Mapped[bool]                    =   mapped_column(Boolean, default=True)
    show_bio:                       Mapped[bool]                    =   mapped_column(Boolean, default=True)
    show_favorites:                 Mapped[bool]                    =   mapped_column(Boolean, default=True)

    # --- Device fingerprint (collected at signup) ---
    device:                         Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    device_name:                    Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    machine:                        Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    os:                             Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    memory:                         Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    hostname:                       Mapped[Optional[str]]           =   mapped_column(String, nullable=True)

    # --- Network / geolocation ---
    country:                        Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    city:                           Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    ip:                             Mapped[Optional[str]]           =   mapped_column(String, nullable=True)

    # --- Account settings ---
    ai_enabled:                     Mapped[bool]                    =   mapped_column(Boolean, nullable=False, default=True, server_default="true")
    max_toasts:                     Mapped[int]                     =   mapped_column(Integer, nullable=False, default=5, server_default="5")
    dm_notifications:               Mapped[bool]                    =   mapped_column(Boolean, nullable=False, default=True, server_default="true")
    muted_users:                    Mapped[Optional[str]]           =   mapped_column(String, nullable=True) # Comma-separated list of IDs

    # --- Account lifecycle ---
    is_deleted:                     Mapped[bool]                    =   mapped_column(Boolean, nullable=False, default=False)
    is_private:                     Mapped[bool]                    =   mapped_column(Boolean, nullable=False, default=False)  # If true, won't show in 'Similar Minds'
    eco_recommendations_enabled:     Mapped[bool]                   =   mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at:                     Mapped[str]                     =   mapped_column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    last_seen:                      Mapped[str]                     =   mapped_column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    # --- Relationships ---
    movies:                         Mapped[List["Movies"]]          = relationship("Movies", back_populates="user", lazy="selectin")
    sent_messages:                  Mapped[List["Message"]]         = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender", cascade="all, delete-orphan")
    received_messages:              Mapped[List["Message"]]         = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver", cascade="all, delete-orphan")
    conversations:                  Mapped[List["Conversation"]]    = relationship("Conversation", primaryjoin="or_(User.id==Conversation.user1_id, User.id==Conversation.user2_id)", viewonly=True)
    ai_messages:                    Mapped[List["AIMessage"]]       = relationship("AIMessage", back_populates="user", cascade="all, delete-orphan")
    notifications:                  Mapped[List["Notification"]]    = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class Movies(Base):
    """
    A movie tracked by a user.

    Each row links a TMDB movie (via `tmdb_id`) to its owning user.
    Genre IDs are stored as a comma-separated string for lightweight
    querying without a many-to-many join table.

    Relationships:
        user            — many-to-one back-reference to User.
        watched_movies  — one-to-many link to WatchedMovies entries.
    """

    __tablename__                                       =   "movies"
    __table_args__                                      =   (UniqueConstraint("user_id", "canonical_id", name="uq_user_canonical_movie"),)

    id:                 Mapped[int]                     =   mapped_column(primary_key=True)
    user_id:            Mapped[int]                     =   mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    canonical_id:       Mapped[str]                     =   mapped_column(String, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    tmdb_id:            Mapped[Optional[int]]           =   mapped_column(Integer, nullable=True, index=True)
    title:              Mapped[str]                     =   mapped_column(String, nullable=False)
    type:               Mapped[str]                     =   mapped_column(String, nullable=False, default="movie")
    overview:           Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    genre_ids:          Mapped[str]                     =   mapped_column(String, nullable=True)  # Comma-separated genre info
    sources:            Mapped[Optional[dict]]          =   mapped_column(JSON, nullable=True)
    vote_average:       Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    poster_url:         Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    release_date:       Mapped[Optional[str]]           =   mapped_column(String, nullable=True)
    status:             Mapped[str]                     =   mapped_column(String, nullable=False, default="Not yet")
    is_favorite:        Mapped[bool]                    =   mapped_column(Boolean, nullable=False, default=False, server_default="false")
    ai_reason:          Mapped[Optional[str]]           =   mapped_column(String, nullable=True)

    user:               Mapped["User"]                  =   relationship("User", back_populates="movies")
    watched_movies:     Mapped[List["WatchedMovies"]]   =   relationship("WatchedMovies",back_populates="movie",lazy="selectin",cascade="all, delete-orphan",)

class WatchedMovies(Base):
    """
    Records when a user marks a movie as 'Watched'.

    This is a separate table from Movies so that a user can track a movie
    (intent to watch) and later confirm they watched it, preserving both
    timestamps independently.
    """

    __tablename__                                   =   "watched_movies"
    __table_args__                                  =   (UniqueConstraint("user_id", "movie_id", name="uq_user_watched_movie"),)

    id:                 Mapped[int]                 =   mapped_column(primary_key=True)
    user_id:            Mapped[int]                 =   mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    movie_id:           Mapped[int]                 =   mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    title:              Mapped[str]                 =   mapped_column(String, nullable=False)
    status:             Mapped[str]                 =   mapped_column(String, nullable=False)
    watched_at:         Mapped[str]                 =   mapped_column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    who_watched:        Mapped["User"]              =   relationship("User")
    movie:              Mapped["Movies"]            =   relationship("Movies", back_populates="watched_movies")

class Message(Base):
    """
    Private message between two users.
    """
    __tablename__                                   =   "messages"

    id:                 Mapped[int]                 =   mapped_column(primary_key=True)
    sender_id:          Mapped[int]                 =   mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    receiver_id:        Mapped[int]                 =   mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content:            Mapped[str]                 =   mapped_column(String, nullable=False)
    is_read:            Mapped[bool]                =   mapped_column(Boolean, default=False)
    message_type:       Mapped[str]                 =   mapped_column(String, default="text", server_default="text") # text, image, movie_recommendation
    attachment_url:     Mapped[Optional[str]]       =   mapped_column(String, nullable=True)
    deleted_by_sender:   Mapped[bool]               =   mapped_column(Boolean, default=False, server_default="false")
    deleted_by_receiver: Mapped[bool]               =   mapped_column(Boolean, default=False, server_default="false")
    is_edited:          Mapped[bool]                =   mapped_column(Boolean, default=False, server_default="false")
    edited_at:          Mapped[Optional[str]]       =   mapped_column(String, nullable=True)
    created_at:         Mapped[str]                 =   mapped_column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat(), index=True)
    sender:             Mapped["User"]              =   relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver:           Mapped["User"]              =   relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")


class Conversation(Base):
    """
    Tracks the status of a conversation between two users (e.g. accepted, pending).
    """
    __tablename__                                   =   "conversations"
    __table_args__                                  =   (
        UniqueConstraint("user1_id", "user2_id", name="uq_user_pair"),
        Index("ix_conv_user1_user2", "user1_id", "user2_id"),
    )

    id:                 Mapped[int]                 =   mapped_column(primary_key=True)
    user1_id:           Mapped[int]                 =   mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user2_id:           Mapped[int]                 =   mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status:             Mapped[str]                 =   mapped_column(String, default="PENDING", server_default="PENDING") # PENDING, ACCEPTED, BLOCKED
    created_at:         Mapped[str]                 =   mapped_column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at:         Mapped[str]                 =   mapped_column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    user1:              Mapped["User"]              =   relationship("User", foreign_keys=[user1_id])
    user2:              Mapped["User"]              =   relationship("User", foreign_keys=[user2_id])


class AIMessage(Base):
    """
    Represents a message in a chat with Eco AI.
    """
    __tablename__                                   =   "ai_messages"

    id:                 Mapped[int]                 =   mapped_column(primary_key=True)
    user_id:            Mapped[int]                 =   mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role:               Mapped[str]                 =   mapped_column(String, nullable=False) # user, assistant
    content:            Mapped[str]                 =   mapped_column(String, nullable=False)
    created_at:         Mapped[str]                 =   mapped_column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat(), index=True)
    user:               Mapped["User"]              =   relationship("User", back_populates="ai_messages")


class SimilarityMatch(Base):
    """
    Pre-calculated similarity between two users to avoid heavy computations on every request.
    Stores why they match (e.g., shared genres or movies).
    """
    __tablename__                                   =   "similarity_matches"
    __table_args__                                  =   (UniqueConstraint("user_id", "target_id", name="uq_user_similarity_pair"),)

    id:                 Mapped[int]                 =   mapped_column(primary_key=True)
    user_id:            Mapped[int]                 =   mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_id:          Mapped[int]                 =   mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    score:              Mapped[float]               =   mapped_column(nullable=False, index=True)
    reasons:            Mapped[Optional[str]]       =   mapped_column(String, nullable=True) # e.g. "Both love Horror"


class Notification(Base):
    """
    Stores system and social notifications for a user.
    """
    __tablename__                                   =   "notifications"

    id:                 Mapped[int]                 =   mapped_column(primary_key=True)
    user_id:            Mapped[int]                 =   mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title:              Mapped[str]                 =   mapped_column(String, nullable=False)
    content:            Mapped[str]                 =   mapped_column(String, nullable=False)
    type:               Mapped[str]                 =   mapped_column(String, default="general", server_default="general") # general, message, match
    is_read:            Mapped[bool]                =   mapped_column(Boolean, default=False, server_default="false")
    created_at:         Mapped[str]                 =   mapped_column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat(), index=True)
    
    user:               Mapped["User"]              =   relationship("User", back_populates="notifications")
    updated_at:         Mapped[str]                 =   mapped_column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())



class RevokedToken(Base):
    """
    Persistent token blacklist.

    Stores JWTs (by their 'jti' claim) that have been explicitly revoked
    (logout, password change, username change).  This survives server
    restarts unlike the previous in-memory cache implementation.

    Rows are purged by a background task once 'expires_at' has passed.
    """
    __tablename__                                   =   "revoked_tokens"

    id:             Mapped[int]                     =   mapped_column(primary_key=True)
    jti:            Mapped[str]                     =   mapped_column(String, unique=True, nullable=False, index=True)
    expires_at:     Mapped[str]                     =   mapped_column(String, nullable=False, index=True)
    revoked_at:     Mapped[str]                     =   mapped_column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# TokenManager — Persistent Token Blacklist
# ---------------------------------------------------------------------------


class TokenManager:
    """
    Manages persistent JWT revocation via the revoked_tokens table.

    Provides three operations:
        revoke()        — Add a JTI to the blacklist.
        is_revoked()    — Check if a JTI is revoked.
        purge_expired() — Clean up rows whose tokens have naturally expired.
    """

    def __init__(self):
        self._session_maker = _session_maker

    @property
    def session(self):
        return self._session_maker

    async def revoke(self, jti: str, expires_at: str):
        """Persist a revoked token's JTI to the database."""
        if not self.session:
            return
        async with self.session() as session:
            try:
                token = RevokedToken(jti=jti, expires_at=expires_at)
                session.add(token)
                await session.commit()
                logger.info(f"Token revoked (jti={jti[:8]}...)")
            except Exception as e:
                await session.rollback()
                logger.warning(f"Token revocation DB write failed: {e}")

    async def is_revoked(self, jti: str) -> bool:
        """Check if a JTI exists in the persistent blacklist."""
        if not self.session:
            return False
        async with self.session() as session:
            stmt = select(RevokedToken).where(RevokedToken.jti == jti)
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def purge_expired(self):
        """Remove expired tokens from the blacklist to keep the table small."""
        if not self.session:
            return
        async with self.session() as session:
            try:
                now = datetime.now(timezone.utc).isoformat()
                stmt = delete(RevokedToken).where(RevokedToken.expires_at < now)
                await session.execute(stmt)
                await session.commit()
                logger.info(f"Purged expired revoked tokens")
            except Exception as e:
                await session.rollback()
                logger.warning(f"Token purge failed: {e}")

# ---------------------------------------------------------------------------
# UserManager
# ---------------------------------------------------------------------------

class UserManager:
    """
    Encapsulates all user-related database operations (async).

    Manages its own async SQLAlchemy engine and session factory.  Every
    public method that mutates data is decorated with `@transaction` to
    guarantee atomic commits or full rollbacks on failure.

    Args:
        db_url: PostgreSQL async connection URL.
        echo:   If True, SQLAlchemy will log all generated SQL.
    """

    def __init__(self):
        """
        Manager uses the globally initialized engine and session maker.
        """
        self._session_maker = _session_maker

    @property
    def engine(self):
        return _engine

    @property
    def session(self):
        return self._session_maker
    
    @session.setter
    def session(self, value):
        self._session_maker = value

    async def create_tables(self):
        """Create all tables in the database (called once at startup)."""
        if self.engine:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

    # --- Decorators ---

    @staticmethod
    def transaction(func):
        """
        Decorator that wraps an async method in a database session context.

        Opens a new async session, calls the decorated function with the
        session as its first positional argument (after `self`), commits
        on success, and rolls back + re-raises on any exception.
        """

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            logger.info(f"TRANSACTION START: {func.__name__}")
            async with self.session() as session:
                try:
                    result = await func(self, session, *args, **kwargs)
                    await session.commit()
                    logger.info(f"TRANSACTION COMMIT: {func.__name__} (Success)")
                    return result
                except Exception as e:
                    await session.rollback()
                    logger.error(f"TRANSACTION ROLLBACK: {func.__name__} - Error: {str(e)}")
                    raise

        return wrapper

    # --- Queries ---

    async def user_exists(self, username: str) -> bool:
        """Check whether a user with the given username exists (non-deleted)."""
        if self.session:
            async with self.session() as session:
                stmt            =   select(User).where(User.username == username, User.is_deleted == False)
                result          =   await session.execute(stmt)
                user            =   result.scalar_one_or_none()
                return user is not None
        return False

    @transaction
    async def add_user(self,session: AsyncSession,user: UserScheme,user_agent: str = "unknown",ip: str = "unknown",) -> bool:
        """
        Register a new user with device and network metadata.
        """
        if user.username.lower() in RESERVED_USERNAMES:
            raise ReservedUsernameError(user.username)

        # Basic User-Agent Parsing logic
        ua                      =   user_agent.lower()
        os_name                 =   "Unknown OS"
        if "windows" in ua:
            os_name             =   "Windows"
        elif "macintosh" in ua or "mac os" in ua:
            os_name             =   "macOS"
        elif "linux" in ua:
            os_name             =   "Linux"
        elif "android" in ua:
            os_name             =   "Android"
        elif "iphone" in ua or "ipad" in ua:
            os_name             =   "IOS"
        device_type             =   "Desktop"
        if "mobile" in ua or "android" in ua or "iphone" in ua:
            device_type         =   "Mobile"
        elif "tablet" in ua or "ipad" in ua:
            device_type         =   "Tablet"
        hashed                  =   await run_in_threadpool(bcrypt.hashpw, user.password.encode("utf-8"), bcrypt.gensalt())
        created_at              =   datetime.now(timezone.utc).isoformat()
        assigned_role           =   "user"
        avatar_url              =   f"https://api.dicebear.com/7.x/avataaars/svg?seed={user.username}"
        
        new_user                =   User(
                    username    =   user.username,
                    role        =   assigned_role,
                    password    =   hashed.decode("utf-8"),
                    email       =   user.email,
                    avatar_url  =   avatar_url,
                    device      =   user.device or device_type,
                    os          =   user.os or os_name,
                    ip          =   ip,
                    device_name =   user_agent[:100],
                    machine     =   user.machine or "Server",
                    memory      =   user.memory or "Unknown",
                    country     =   "Pending",
                    city        =   "Pending",
                    ai_enabled  =   True,
                    eco_recommendations_enabled = True,
                    is_deleted  =   False,
                    created_at  =   created_at,
                    last_seen   =   created_at,
        )
        session.add(new_user)
        logger.info(f"Adding user: {new_user.username} - {new_user.email}")
        return True

    @transaction
    async def delete_user(self, session: AsyncSession, username: str) -> bool:
        """
        Soft-delete a user by setting `is_deleted = True`.

        The record remains in the database for auditing but will not
        appear in normal queries.

        Raises:
            UserNotFoundError: If no user with the given username exists.
        """
        stmt                =   select(User).where(User.username == username)
        result              =   await session.execute(stmt)
        user                =   result.scalar_one_or_none()
        
        if not user:
            raise UserNotFoundError(username)
        
        if hasattr(user, "is_deleted"):
            setattr(user, "is_deleted", True)
        
        logger.info(f"Deleted user: {user.username}")
        return True

    async def ensure_admin_exists(self) -> None:
        """
        Ensures at least one admin exists in the system.
        """
        username                =   os.getenv("INITIAL_ADMIN_USERNAME")
        password                =   os.getenv("INITIAL_ADMIN_PASSWORD")
        email                   =   os.getenv("INITIAL_ADMIN_EMAIL")

        if not username or not password or not email:
            logger.warning("Initial admin credentials not fully provided. Skipping superuser seeding.")
            return

        if not self.session:
            return

        async with self.session() as session:
            # Check if ANY admin already exists in the system
            stmt                    =   select(User).where(User.role == "admin")
            result                  =   await session.execute(stmt)
            
            if result.scalar_one_or_none():
                logger.info("Admin seed: At least one admin already exists. Skipping superuser seeding.")
                return

            # Seed the superuser
            hashed                  =   await run_in_threadpool(bcrypt.hashpw, password.encode("utf-8"), bcrypt.gensalt())
            created_at              =   datetime.now(timezone.utc).isoformat()

            new_admin               =   User(
                        username    =   username,
                        password    =   hashed.decode("utf-8"),
                        email       =   email,
                        role        =   "admin",
                        is_deleted  =   False,
                        created_at  =   created_at,
                        last_seen   =   created_at,
                        city        =   "System",
                        country     =   "System",
                        ip          =   "127.0.0.1",
                        ai_enabled  =   True,
                    )

            try:
                session.add(new_admin)
                await session.commit()
                logger.info(f"Successfully seeded superuser: {username}")
            except Exception as e:
                await session.rollback()
                logger.warning(f"Admin seeding conflict (likely another worker): {type(e).__name__}")

    @transaction
    async def update_last_seen(self, session: AsyncSession, username: str) -> None:
        """
        Update the last_seen timestamp for a user to the current time.
        """
        stmt    = select(User).where(User.username == username, User.is_deleted == False)
        result  = await session.execute(stmt)
        user    = result.scalar_one_or_none()
        if user:
            user.last_seen = datetime.now(timezone.utc).isoformat()

    @transaction
    async def get_user_by_username(self, session: AsyncSession, username: str) -> dict:
        """
        Retrieve a single user record by username.

        Returns:
            dict mapping column names to their values.

        Raises:
            UserNotFoundError: If no matching user is found.
        """
        stmt    = select(User).where(User.username == username, User.is_deleted == False)
        result  = await session.execute(stmt)
        user    = result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(username)
        return {c.name: getattr(user, c.name) for c in user.__table__.columns}

    @transaction
    async def get_user_by_email(self, session: AsyncSession, email: str) -> dict | None:
        """Fetch a user record by email address."""
        stmt    = select(User).where(User.email == email, User.is_deleted == False)
        result  = await session.execute(stmt)
        user    = result.scalar_one_or_none()
        if user:
            return {c.name: getattr(user, c.name) for c in user.__table__.columns}
        return None

    @transaction
    async def get_or_create_google_user(self, session: AsyncSession, email: str, name: str, avatar_url: str | None = None, ip: str = "Unknown", user_agent: str = "Unknown") -> dict:
        """Finds a user by email or creates a new one if they don't exist (OAuth)."""
        stmt            =   select(User).where(User.email == email, User.is_deleted == False)
        result          =   await session.execute(stmt)
        user            =   result.scalar_one_or_none()
        
        if user:
            user.last_seen  =   datetime.now(timezone.utc).isoformat()
            return {c.name: getattr(user, c.name) for c in user.__table__.columns}
        # Create new user
        base_username   =   email.split("@")[0].replace(".", "_")
        username        =   base_username
        # Unique username check
        counter         =   1
        while True:
            exists_stmt =   select(User).where(User.username == username)
            exists_res  =   await session.execute(exists_stmt)
            if not exists_res.scalar_one_or_none():
                break
            username    =   f"{base_username}{counter}"
            counter     +=  1
        random_pass     =   secrets.token_urlsafe(32)
        hashed          =   await run_in_threadpool(bcrypt.hashpw, random_pass.encode("utf-8"), bcrypt.gensalt())
        created_at      =   datetime.now(timezone.utc).isoformat()
        if not avatar_url:
            avatar_url  =   f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}"

        new_user        =   User(
                    username    =   username,
                    role        =   "user",
                    password    =   hashed.decode("utf-8"),
                    email       =   email,
                    avatar_url  =   avatar_url,
                    device      =   "Desktop",
                    os          =   "Unknown",
                    ip          =   ip,
                    device_name =   user_agent[:100],
                    ai_enabled  =   True,
                    is_deleted  =   False,
                    created_at  =   created_at,
                    last_seen   =   created_at,
        ) # type: ignore
        
        session.add(new_user)
        await session.flush()
        
        return {c.name: getattr(new_user, c.name) for c in new_user.__table__.columns}

    @transaction
    async def get_user_by_id(self, session: AsyncSession, id: int) -> dict:
        """
        Retrieve a single user record by primary key (Fixed 5.2: Filters deleted).
        """
        stmt            =   select(User).where(User.id == id, User.is_deleted == False)
        result          =   await session.execute(stmt)
        user            =   result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(str(id))
        return {c.name: getattr(user, c.name) for c in user.__table__.columns if c.name not in SENSITIVE_FIELDS}

    @transaction
    async def get_all_users(self, session: AsyncSession, skip: int = 0, limit: int = 10) -> list[dict]:
        """
        Return a paginated list of all user records.

        Args:
            skip:  Number of rows to skip (offset).
            limit: Maximum number of rows to return (hard max: 100).
        """
        limit = min(limit, 100)  # Hard maximum to prevent unbounded queries
        skip = max(skip, 0)
        stmt            =   select(User).offset(skip).limit(limit)
        result          =   await session.execute(stmt)
        users           =   result.scalars().all()
        return [{c.name: getattr(u, c.name) for c in u.__table__.columns if c.name not in SENSITIVE_FIELDS} for u in users]

    @transaction
    async def update_profile(self, session: AsyncSession, username: str, data: dict) -> bool:
        """
        Update multiple profile fields at once.
        """
        stmt = select(User).where(User.username == username, User.is_deleted == False)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return False

        for key, value in data.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        
        return True
        
    @transaction
    async def update_user_field(self, session: AsyncSession,username: str, field: str, value: Any, current_password: str | None = None) -> bool:
        """
        Update a single field on a user record.

        Sensitive updates (password, email) require 'current_password' verification.
        Enforces a whitelist of allowed fields to prevent privilege escalation.

        Raises:
            UserNotFoundError: If the target user does not exist.
            ValueError: If an unauthorized field is requested or password verification fails.
        """
        stmt                        =   select(User).where(User.username == username)
        result                      =   await session.execute(stmt)
        user                        =   result.scalar_one_or_none()
        
        if not user:
            raise UserNotFoundError(username)

        f_lower                     =   field.lower()
        ALLOWED_FIELDS              =   {
            "password", "email", "ai_enabled", "username", "nickname", "max_toasts", "avatar_url", 
            "bio", "gender", "age", "location", "social_link", "full_name", "social_links", "favorite_genres",
            "show_age", "show_gender", "show_location", "show_bio", "show_favorites", "is_private",
            "eco_recommendations_enabled", "dm_notifications"
        }
        if user.role == "admin" and field == "username":
            logger.warning(f"Admin cannot update username for user {username}")
            raise ValueError("Admin cannot update username. ")
    
        if f_lower not in ALLOWED_FIELDS:
            logger.warning(f"Unauthorized update attempt on field '{field}' for user {username}")
            raise ValueError(f"Field '{field}' cannot be updated via this endpoint.")

        # Require password verification for sensitive changes
        if f_lower in {"password", "email", "username"}:
            if not current_password:
                raise ValueError("Current password is required to change this setting.")

            # Verify current password (offloaded to threadpool to avoid blocking event loop)
            stored_hash = user.password.encode("utf-8")
            if not await run_in_threadpool(bcrypt.checkpw, current_password.encode("utf-8"), stored_hash):
                logger.warning(f"Failed password verification for user {username}")
                raise ValueError("Invalid current password.")

            # Prevent updating to the exact same value
            if f_lower == "email":
                if value.lower() == user.email.lower():
                    raise ValueError("New email must be different from your current one.")

            if f_lower == "password":
                if await run_in_threadpool(bcrypt.checkpw, value.encode("utf-8"), stored_hash):
                    raise ValueError("New password must be different from your current one.")

            if f_lower == "username":
                if value.lower() == user.username.lower():
                    raise ValueError("New username must be different from your current one.")

        if f_lower == "password":
            hashed                  =   await run_in_threadpool(bcrypt.hashpw, value.encode("utf-8"), bcrypt.gensalt())
            setattr(user, "password", hashed.decode("utf-8"))
            return True

        if f_lower == "ai_enabled":
            bool_value              =   str(value).lower() in ("true", "1", "yes", "t")
            setattr(user, "ai_enabled", bool_value)
            return True

        if f_lower == "eco_recommendations_enabled":
            bool_value              =   str(value).lower() in ("true", "1", "yes", "t")
            setattr(user, "eco_recommendations_enabled", bool_value)
            return True

        if f_lower == "max_toasts":
            try:
                val                 =   int(value)
                if val < 1 or val > 20:
                    raise ValueError("Max toasts must be between 1 and 20.")
                
                setattr(user, "max_toasts", val)
                return True
            
            except (TypeError, ValueError):
                raise ValueError("Invalid value for max_toasts. Must be a number.")

        if f_lower == "username":
            # Check for uniqueness
            stmt = select(User).where(User.username == value)
            existing = await session.execute(stmt)
            if existing.scalar_one_or_none():
                raise ValueError(f"Username '{value}' is already taken.")
            setattr(user, "username", value)
            return True

        # For general fields, we just set it directly
        setattr(user, f_lower, value)
        logger.info(f"DATABASE UPDATE: User '{username}' field '{field}' set to '{value}'")
        return True


class AIManager:
    """
    Manages persistence for AI chat interactions.
    """

    def __init__(self):
        self._session_maker = _session_maker

    @property
    def session(self):
        return self._session_maker

    @staticmethod
    def transaction(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            async with self.session() as session:
                try:
                    result = await func(self, session, *args, **kwargs)
                    await session.commit()
                    return result
                except Exception as e:
                    await session.rollback()
                    logger.error(f"AI TRANSACTION ERROR: {str(e)}")
                    raise
        return wrapper

    @transaction
    async def add_message(self, session: AsyncSession, username: str, role: str, content: str):
        stmt = select(User).where(User.username == username)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            return
        
        new_msg = AIMessage(user_id=user.id, role=role, content=content)
        session.add(new_msg)

        # Prune old messages — keep at most 40 per user to bound prompt size and DB growth
        count_stmt = select(func.count(AIMessage.id)).where(AIMessage.user_id == user.id)
        count = (await session.execute(count_stmt)).scalar() or 0
        if count > 40:
            oldest_stmt = (
                select(AIMessage.id)
                .where(AIMessage.user_id == user.id)
                .order_by(AIMessage.created_at.asc())
                .limit(count - 40)
            )
            oldest_ids = (await session.execute(oldest_stmt)).scalars().all()
            if oldest_ids:
                await session.execute(delete(AIMessage).where(AIMessage.id.in_(oldest_ids)))

    @transaction
    async def get_history(self, session: AsyncSession, username: str, limit: int = 20):
        stmt = select(User).where(User.username == username)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            return []
        
        msg_stmt = select(AIMessage).where(AIMessage.user_id == user.id).order_by(AIMessage.created_at.asc()).limit(limit)
        msg_res = await session.execute(msg_stmt)
        return msg_res.scalars().all()
    
    @transaction
    async def clear_history(self, session: AsyncSession, username: str):
        stmt = select(User).where(User.username == username)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            return
        
        del_stmt = delete(AIMessage).where(AIMessage.user_id == user.id)
        await session.execute(del_stmt)



class NotificationManager:
    """
    Manages user notifications (messages, matches, etc.).
    """

    def __init__(self):
        self._session_maker = _session_maker

    @property
    def session(self):
        return self._session_maker

    @staticmethod
    def transaction(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            async with self.session() as session:
                try:
                    result = await func(self, session, *args, **kwargs)
                    await session.commit()
                    return result
                except Exception as e:
                    await session.rollback()
                    logger.error(f"NOTIFICATION TRANSACTION ERROR: {str(e)}")
                    raise
        return wrapper

    @transaction
    async def create_notification(self, session: AsyncSession, user_id: int, title: str, content: str, type: str = "general"):
        notif = Notification(user_id=user_id, title=title, content=content, type=type)
        session.add(notif)
        return notif

    @transaction
    async def get_notifications(self, session: AsyncSession, user_id: int, limit: int = 50):
        stmt = select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc()).limit(limit)
        res = await session.execute(stmt)
        return res.scalars().all()

    @transaction
    async def mark_as_read(self, session: AsyncSession, user_id: int, notification_id: Optional[int] = None ):
        if notification_id:
            stmt = update(Notification).where(Notification.id == notification_id, Notification.user_id == user_id).values(is_read=True)
        else:
            stmt = update(Notification).where(Notification.user_id == user_id, Notification.is_read == False).values(is_read=True)
        await session.execute(stmt)
        return True

    @transaction
    async def get_unread_count(self, session: AsyncSession, user_id: int):
        stmt = select(func.count(Notification.id)).where(Notification.user_id == user_id, Notification.is_read == False)
        res = await session.execute(stmt)
        return res.scalar() or 0


class MovieManager:
    """
    Encapsulates all movie-related database operations (async).

    Handles tracking, deletion, status updates, and genre-based
    recommendation lookups against the TMDB API.

    Args:
        db_url: PostgreSQL async connection URL.
        echo:   If True, SQLAlchemy will log all generated SQL.
    """

    def __init__(self):
        """
        Manager uses the globally initialized engine and session maker.
        """
        self._session_maker = _session_maker

    @property
    def engine(self):
        return _engine

    @property
    def session(self):
        return self._session_maker
    
    @session.setter
    def session(self, value):
        self._session_maker = value

    @staticmethod
    def transaction(func):
        """
        Decorator that wraps an async method in a database session context.

        Identical to UserManager.transaction — duplicated here because
        each manager owns its own engine/session factory.
        """

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            logger.info(f"Running function: {func.__name__}")
            async with self.session() as session:
                try:
                    result          =   await func(self, session, *args, **kwargs)
                    await session.commit()
                    logger.info(f"Done function: {func.__name__}")
                    return result
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Error in function: {func.__name__} - {str(e)}")
                    raise

        return wrapper

    async def get_top_genres(self, username: str) -> list:
        """
        Analyse a user's tracked movies and return the top 5 most
        frequently occurring TMDB genre IDs.

        This powers the recommendation engine: the returned IDs are
        passed to TMDB's /discover endpoint to find similar films.

        Returns:
            List of up to 5 integer genre IDs, sorted by frequency
            (most common first).  Empty list if the user has no movies.
        """
        if self.session:
            async with self.session() as session:
                stmt            =   (select(Movies.genre_ids).join(User, User.id == Movies.user_id).where(User.username == username))
                result          =   await session.execute(stmt)
                genre_rows      =   result.scalars().all()

            genre_ids           =   ",".join(genre_rows)
            genre_ids           =   genre_ids.strip(",")
            
            if not genre_ids or genre_ids is None:
                logger.info(f"User {username} hasn't rated/watched enough categories yet.")
                return []
            
            ids                 =   []
            for i in genre_ids.split(","):
                try:
                    ids.append(int(i.strip()))
                except ValueError:
                    continue
            
            if not ids:
                return []
                
            count               =   Counter(ids)
            top_genres          =   [item for item, _ in count.most_common(5)]
            
            return top_genres
        
        return []
    
    @transaction
    async def get_watched_movies(self, session: AsyncSession, username: str, skip: int = 0, limit: int = 10) -> list[dict]:
        """
        Return a paginated list of movies tracked by the given user.

        Pagination is performed at the SQL level (OFFSET/LIMIT) to avoid
        loading all movies into memory.

        Args:
            username: Owner of the movie collection.
            skip:     Number of items to skip (offset).
            limit:    Maximum number of items to return.

        Raises:
            UserNotFoundError: If no user with the given username exists.
        """
        # Verify user exists without loading the full relationship graph
        user_stmt               =   select(User.id).where(User.username == username)
        user_result             =   await session.execute(user_stmt)
        user_row                =   user_result.scalar_one_or_none()
        
        if user_row is None:
            raise UserNotFoundError(username)

        # Enforce hard pagination limits
        limit                   =   min(limit, 50)
        skip                    =   max(skip, 0)

        if limit == 50:
            logger.warning(f"⚠️ Warning: Hard pagination limit of {limit} reached for user {username}")
            
        # SQL-level pagination — only fetches the requested slice
        movies_stmt             =   (select(Movies).where(Movies.user_id == user_row).order_by(Movies.id.desc()).offset(skip).limit(limit))
        movies_result           =   await session.execute(movies_stmt)
        movies                  =   movies_result.scalars().all()
        
        return [{c.name: getattr(m, c.name) for c in m.__table__.columns} for m in movies]

    @transaction
    async def get_all_tracked_tmdb_ids(self, session: AsyncSession, username: str) -> set[int]:
        """
        Return a set of all TMDB IDs tracked by the given user.
        Used for filtering recommendations.
        """
        stmt                    =   (select(Movies.tmdb_id).join(User, User.id == Movies.user_id).where(User.username == username))
        result                  =   await session.execute(stmt)
        return set(result.scalars().all())  #type: ignore

    @transaction
    async def get_favorite_tmdb_ids(self, session: AsyncSession, username: str) -> set[int]:
        """
        Return a set of TMDB IDs that are marked as favorites by the user.
        """
        stmt = (
            select(Movies.tmdb_id)
            .join(User, User.id == Movies.user_id)
            .where(User.username == username, Movies.is_favorite == True)
        )
        result = await session.execute(stmt)
        return set(result.scalars().all()) # type: ignore

    @transaction
    async def delete_movie(self, session: AsyncSession, username: str, movie_id: int) -> bool:
        """
        Remove a movie from a user's tracked collection by its database ID.

        Uses the primary key directly — no external API dependency required.

        Raises:
            UserNotFoundError:  If the user does not exist.
            MovieNotFoundError: If the movie is not in the user's list.
        """
        stmt                =   select(User).where(User.username == username)
        result              =   await session.execute(stmt)
        user                =   result.scalar_one_or_none()
        
        if not user:
            raise UserNotFoundError(username)

        movie_stmt          =   select(Movies).where(Movies.id == movie_id, Movies.user_id == user.id)
        movie_result        =   await session.execute(movie_stmt)
        movie               =   movie_result.scalar_one_or_none()
        
        if not movie:
            raise MovieNotFoundError(str(movie_id))

        await session.delete(movie)
        
        logger.info(f"Deleted movie: {movie.title} (id={movie_id}) - {user.username}")
        
        return True

    @transaction
    async def update_status(self, session: AsyncSession, username: str, status: str, query: str) -> bool:
        """
        Mark a tracked movie with a new status (e.g. 'Watched').

        Creates a WatchedMovies record with the current UTC timestamp.

        Raises:
            MovieNotFoundError: If the movie is not in the user's tracked list or TMDB fails.
            MovieAlreadyExists: If the movie already has a WatchedMovies entry.
            UserNotFoundError:  If the user does not exist.
        """
        data                        =   await fetch_tmdb_data(query)
        if not data:
            raise MovieNotFoundError(query)

        stmt            =   select(User).where(User.username == username, User.is_deleted == False)
        result          =   await session.execute(stmt)
        user            =   result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(username)

        movie_stmt      =   select(Movies).where(Movies.user_id == user.id, Movies.tmdb_id == data.get("tmdb_id"))
        movie_result    =   await session.execute(movie_stmt)
        movie           =   movie_result.scalar_one_or_none()
        if not movie:
            raise MovieNotFoundError(data.get("title", query))

        # Update status on the tracked movie
        movie.status    =   status

        if status == "Watched":
            # Check if already marked as watched
            already_watched_stmt        =   select(WatchedMovies).where(WatchedMovies.user_id == user.id,WatchedMovies.movie_id == movie.id,)
            already_watched_result      =   await session.execute(already_watched_stmt)
            
            if already_watched_result.scalar_one_or_none():
                raise MovieAlreadyExists(movie.title)

            watched_entry               =   WatchedMovies(user_id=user.id,movie_id=movie.id,title=movie.title,status=status,watched_at=datetime.now(timezone.utc).isoformat(),)
            
            session.add(watched_entry)
        
        else:
            # If changed from Watched to something else, remove from WatchedMovies
            await session.execute(delete(WatchedMovies).where(WatchedMovies.user_id == user.id,WatchedMovies.movie_id == movie.id,))
        
        return True
        
    @transaction
    async def add_movie(self, session: AsyncSession, username: str, movie_data: MovieScheme) -> bool:
        """
        Add a movie to the user's tracked list.
        
        Supports two flows:
        1. Legacy (tmdb_id only): Fetches full data from TMDB, generates canonical_id.
        2. New (canonical_id + sources): Stores the canonical entity directly.
        """
        stmt            =   select(User).where(User.username == username, User.is_deleted == False)
        result          =   await session.execute(stmt)
        user            =   result.scalar_one_or_none()

        if not user:
            raise UserNotFoundError(username)

        # --- Legacy flow: tmdb_id provided, no canonical_id ---
        if movie_data.tmdb_id and not movie_data.canonical_id:
            # Check duplicate by tmdb_id
            dup_stmt    =   select(Movies).where(Movies.user_id == user.id, Movies.tmdb_id == movie_data.tmdb_id)
            dup_result  =   await session.execute(dup_stmt)
            if dup_result.scalar_one_or_none():
                raise MovieAlreadyExists(movie_data.title or str(movie_data.tmdb_id))

            # Fetch full data from TMDB
            data = await fetch_tmdb_movie_by_id(movie_data.tmdb_id)
            if not data and movie_data.query:
                data = await fetch_tmdb_data(movie_data.query)
            if not data:
                raise MovieNotFoundError(movie_data.query or str(movie_data.tmdb_id))

            movie       =   Movies(
                                user_id         =   user.id,
                                canonical_id    =   str(uuid.uuid4()),
                                tmdb_id         =   data.get("tmdb_id"),
                                title           =   data.get("title", "Unknown"),
                                type            =   "movie",
                                sources         =   {"tmdb": {"id": str(data.get("tmdb_id")), "provider_name": "tmdb"}},
                                overview        =   data.get("overview", ""),
                                genre_ids       =   data.get("genre_ids", ""),
                                status          =   "Not yet",
                                vote_average    =   data.get("vote_average"),
                                poster_url      =   data.get("poster_url"),
                                release_date    =   data.get("release_date"),
                                ai_reason       =   movie_data.ai_reason or data.get("ai_reason", "")
                            )
            session.add(movie)
            return True

        # --- New flow: canonical_id provided ---
        canonical_id = movie_data.canonical_id or str(uuid.uuid4())

        # Check duplicate by canonical_id
        is_exist_stmt   =   select(Movies).where(Movies.user_id == user.id, Movies.canonical_id == canonical_id)
        is_exist_result =   await session.execute(is_exist_stmt)
        if is_exist_result.scalar_one_or_none():
            raise MovieAlreadyExists(movie_data.title or "Unknown")
        
        movie       =   Movies(
                            user_id         =   user.id,
                            canonical_id    =   canonical_id,
                            tmdb_id         =   movie_data.tmdb_id,
                            title           =   movie_data.title or "Unknown",
                            type            =   movie_data.type or "movie",
                            sources         =   movie_data.sources,
                            overview        =   movie_data.overview or "",
                            genre_ids       =   movie_data.genre_ids or "",
                            status          =   "Not yet",
                            vote_average    =   str(movie_data.vote_average) if movie_data.vote_average is not None else None,
                            poster_url      =   movie_data.poster_url,
                            release_date    =   movie_data.release_date,
                            ai_reason       =   movie_data.ai_reason or "",
                        )

        session.add(movie)
        return True

    @transaction
    async def toggle_favorite(self, session: AsyncSession, username: str, movie_id: int) -> dict:
        """
        Toggle the is_favorite status of a movie.
        Restricts favorites to a maximum of 3 per user.
        """
        user_stmt = select(User).where(User.username == username, User.is_deleted == False)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(username)

        movie_stmt = select(Movies).where(Movies.id == movie_id, Movies.user_id == user.id)
        movie_result = await session.execute(movie_stmt)
        movie = movie_result.scalar_one_or_none()
        
        if not movie:
            raise MovieNotFoundError(str(movie_id))

        if not movie.is_favorite:
            # Check how many favorites they already have
            fav_count_stmt = select(Movies).where(Movies.user_id == user.id, Movies.is_favorite == True)
            fav_count_res = await session.execute(fav_count_stmt)
            current_favorites = fav_count_res.scalars().all()
            if len(current_favorites) >= 3:
                raise ValueError("You can only have up to 3 favorites.")
            movie.is_favorite = True
            is_fav = True
        else:
            movie.is_favorite = False
            is_fav = False
            
        return {"success": True, "is_favorite": is_fav}
        
    @transaction
    async def get_favorites(self, session: AsyncSession, username: str) -> List[dict]:
        """Fetch all favorite movies for a user."""
        user_stmt = select(User).where(User.username == username, User.is_deleted == False)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(username)

        stmt = select(Movies).where(Movies.user_id == user.id, Movies.is_favorite == True).order_by(Movies.id.desc())
        result = await session.execute(stmt)
        movies = result.scalars().all()
        return [{c.name: getattr(m, c.name) for c in m.__table__.columns} for m in movies]

    @transaction
    async def sort_by_release_date(self, session: AsyncSession, username: str) -> List[dict]:
        """Fetch all rated movies for a user within the given rating range."""
        user_stmt = select(User).where(User.username == username, User.is_deleted == False)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(username)

        stmt = select(Movies).where(Movies.user_id == user.id).order_by(Movies.release_date.desc())
        result = await session.execute(stmt)
        movies = result.scalars().all()
        return [{c.name: getattr(m, c.name) for c in m.__table__.columns} for m in movies]


class SocialManager:
    """
    Handles all social-related database operations:
    Messaging, Similar Minds discovery, and User Profiles.
    """

    def __init__(self):
        """
        Manager uses the globally initialized engine and session maker.
        """
        self._session_maker = _session_maker

    @property
    def engine(self):
        return _engine

    @property
    def session(self):
        return self._session_maker
    
    @session.setter
    def session(self, value):
        self._session_maker = value

    @staticmethod
    def transaction(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            async with self.session() as session:
                try:
                    result = await func(self, session, *args, **kwargs)
                    await session.commit()
                    return result
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Error in {func.__name__}: {str(e)}")
                    raise

        return wrapper

    @transaction
    async def get_similar_users(self, session: AsyncSession, user_id: int, limit: int = 5) -> list[dict]:
        """
        Fetch pre-calculated similar users for the given user ID.
        Skips private accounts and the user themselves.
        """
        # Subquery to find IDs of users already in conversations
        messaged_subq = select(Conversation.user1_id).where(Conversation.user2_id == user_id).union(
            select(Conversation.user2_id).where(Conversation.user1_id == user_id)
        )

        stmt = (
            select(SimilarityMatch, User)
            .join(User, User.id == SimilarityMatch.target_id)
            .where(SimilarityMatch.user_id == user_id)
            .where(User.is_private == False)
            .where(User.is_deleted == False)
            .where(User.id != user_id)
            .where(User.id.notin_(messaged_subq))
            .order_by(SimilarityMatch.score.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        matches = result.all()

        return [
            {
                "target_user": {
                    "id": user.id,
                    "username": user.username,
                    "nickname": user.nickname,
                    "avatar_url": user.avatar_url,
                    "bio": user.bio if user.show_bio else None,
                    "last_seen": user.last_seen,
                },
                "score": sim.score,
                "reasons": sim.reasons,
            }
            for sim, user in matches
        ]

    @transaction
    async def send_message(self, session: AsyncSession, sender_id: int, receiver_id: int, content: str, message_type: str = "text", attachment_url: str | None = None) -> Message:
        """
        Send a private message. Ensures a Conversation record exists.
        Initial status is PENDING if it's the first message ever.
        """
        if sender_id == receiver_id:
            raise ValueError("You cannot send a message to yourself.")

        # Ensure conversation exists
        u1, u2 = sorted([sender_id, receiver_id])
        stmt = select(Conversation).where(Conversation.user1_id == u1, Conversation.user2_id == u2)
        res = await session.execute(stmt)
        conv = res.scalar_one_or_none()

        if not conv:
            # First message ever between these two -> PENDING
            conv = Conversation(user1_id=u1, user2_id=u2, status="PENDING")
            session.add(conv)
            await session.flush()
        
        # Update conversation timestamp
        conv.updated_at = datetime.now(timezone.utc).isoformat()

        msg = Message(
            sender_id=sender_id, 
            receiver_id=receiver_id, 
            content=content,
            message_type=message_type,
            attachment_url=attachment_url
        )
        session.add(msg)
        await session.flush()

        # Trigger notification only if receiver has DM notifications enabled
        receiver_pref_stmt = select(User.dm_notifications).where(User.id == receiver_id)
        receiver_pref_res = await session.execute(receiver_pref_stmt)
        dm_enabled = receiver_pref_res.scalar()

        if dm_enabled is not False:  # Default to True if column is None
            from services.deps import notification_manager
            await notification_manager.create_notification(user_id=receiver_id,title="New Message",content=f"You received a message: {content[:30]}...",type="message") #type: ignore   
        return msg

    @transaction
    async def edit_message(self, session: AsyncSession, message_id: int, user_id: int, new_content: str) -> Message:
        """
        Edit an existing message if the user is the sender.
        """
        stmt = select(Message).where(Message.id == message_id, Message.sender_id == user_id)
        res = await session.execute(stmt)
        msg = res.scalar_one_or_none()

        if not msg:
            raise ValueError("Message not found or you are not the sender.")

        msg.content = new_content
        msg.is_edited = True
        msg.edited_at = datetime.now(timezone.utc).isoformat()
        return msg

    @transaction
    async def delete_message(self, session: AsyncSession, message_id: int, user_id: int):
        """
        Hard delete a message — only the sender may delete their own messages.
        SELECT first to verify ownership before issuing the DELETE.
        A DELETE statement returns a CursorResult, not a scalar — checking
        scalar_one_or_none() on a DELETE always returns None, making any
        post-delete ownership check impossible. We must SELECT then DELETE.
        """
        stmt    = select(Message).where(Message.id == message_id, Message.sender_id == user_id)
        res     = await session.execute(stmt)
        msg     = res.scalar_one_or_none()
        
        if not msg:
            raise ValueError("Message not found or you are not the sender")

        await session.delete(msg)

    @transaction
    async def handle_request(self, session: AsyncSession, user_id: int, other_id: int, action: str):
        """
        Accept or Decline a message request.
        Finds the conversation regardless of who is user1 or user2.
        """
        stmt = select(Conversation).where(
            or_(
                and_(Conversation.user1_id == user_id, Conversation.user2_id == other_id),
                and_(Conversation.user1_id == other_id, Conversation.user2_id == user_id)
            )
        )
        res = await session.execute(stmt)
        conv = res.scalar_one_or_none()

        if not conv:
            raise ValueError("No conversation request found.")

        if action == "accept":
            conv.status = "ACCEPTED"
            conv.updated_at = datetime.now(timezone.utc).isoformat()
        elif action == "decline":
            # Delete conversation and all messages
            await session.execute(delete(Message).where(
                or_(
                    and_(Message.sender_id == user_id, Message.receiver_id == other_id),
                    and_(Message.sender_id == other_id, Message.receiver_id == user_id)
                )
            ))
            await session.execute(delete(Conversation).where(Conversation.id == conv.id))
        return True

    @transaction
    async def get_messages(self, session: AsyncSession, user_a: int, user_b: int, skip: int = 0, limit: int = 50) -> List[dict]:
        """
        Get the full chat history between two users, ordered chronologically.
        """
        stmt = select(Message).where(
            or_(
                and_(Message.sender_id == user_a, Message.receiver_id == user_b, Message.deleted_by_sender == False),
                and_(Message.sender_id == user_b, Message.receiver_id == user_a, Message.deleted_by_receiver == False)
            )
        ).order_by(Message.created_at.desc()).offset(skip).limit(limit)
        
        result = await session.execute(stmt)
        messages = result.scalars().all()
        # Reverse to chronological order after desc fetch
        messages = messages[::-1]
        
        return [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "receiver_id": m.receiver_id,
                "content": m.content,
                "is_read": m.is_read,
                "is_edited": m.is_edited,
                "edited_at": m.edited_at,
                "message_type": m.message_type,
                "attachment_url": m.attachment_url,
                "created_at": m.created_at
            }
            for m in messages
        ]

    @transaction
    async def get_conversations(self, session: AsyncSession, user_id: int, status: str = "ACCEPTED", skip: int = 0, limit: int = 50) -> List[dict]:
        """
        Get all conversations for a user with specific status.
        ACCEPTED: Normal inbox (includes sender's PENDING conversations as PENDING_SENT).
        PENDING: Message requests (only where current user is receiver of first message).
        """
        if status == "ACCEPTED":
            # For ACCEPTED view: show accepted convos AND pending convos where I am the sender
            stmt = select(Conversation).where(
                or_(Conversation.user1_id == user_id, Conversation.user2_id == user_id),
                or_(Conversation.status == "ACCEPTED", Conversation.status == "PENDING")
            )
        else:
            # For PENDING view: show pending convos (receiver will be filtered below)
            stmt = select(Conversation).where(
                or_(Conversation.user1_id == user_id, Conversation.user2_id == user_id),
                Conversation.status == "PENDING"
            )
        
        from sqlalchemy.orm import joinedload
        # Fix 5.4: Use joinedload for user1/user2 to avoid N+1
        stmt = stmt.options(joinedload(Conversation.user1), joinedload(Conversation.user2)).offset(skip).limit(limit)
        res = await session.execute(stmt)
        convs = res.scalars().all()
        
        results = []
        seen_others = set()
        for c in convs:
            other_id = c.user2_id if c.user1_id == user_id else c.user1_id
            
            # Prevent showing the same user twice if duplicate records exist
            if other_id in seen_others:
                continue
            seen_others.add(other_id)
            
            # Determine if I am the sender or receiver of this conversation request
            is_sender_of_request = False
            if c.status == "PENDING":
                first_msg_stmt = select(Message).where(
                    or_(
                        and_(Message.sender_id == user_id, Message.receiver_id == other_id),
                        and_(Message.sender_id == other_id, Message.receiver_id == user_id)
                    )
                ).order_by(Message.created_at.asc()).limit(1)
                first_msg_res = await session.execute(first_msg_stmt)
                first_msg = first_msg_res.scalar()
                
                if first_msg:
                    is_sender_of_request = (first_msg.sender_id == user_id)
                
                # For PENDING tab: skip if I am the sender (I shouldn't see my own requests here)
                if status == "PENDING" and is_sender_of_request:
                    continue
                
                # For ACCEPTED tab: skip if I am the receiver (they should see it in PENDING tab)
                if status == "ACCEPTED" and not is_sender_of_request:
                    continue

            # Get last message
            last_msg_stmt = select(Message).where(
                or_(
                    and_(Message.sender_id == user_id, Message.receiver_id == other_id, Message.deleted_by_sender == False),
                    and_(Message.sender_id == other_id, Message.receiver_id == user_id, Message.deleted_by_receiver == False)
                )
            ).order_by(Message.created_at.desc()).limit(1)
            
            last_msg_res = await session.execute(last_msg_stmt)
            last_msg = last_msg_res.scalar_one_or_none()
            
            if not last_msg: continue
            
            # Get unread count
            unread_stmt = select(func.count(Message.id)).where(
                Message.sender_id == other_id,
                Message.receiver_id == user_id,
                Message.is_read == False,
                Message.deleted_by_receiver == False
            )
            unread_res = await session.execute(unread_stmt)
            unread_count = unread_res.scalar() or 0
            
            # Fix 5.4: Use joined participant info from joinedload
            participant = c.user2 if c.user1_id == user_id else c.user1
            
            if not participant: continue
            
            # Determine the display status
            display_status = c.status
            if c.status == "PENDING" and is_sender_of_request:
                display_status = "PENDING_SENT"
            
            results.append({
                "participant": {
                    "id": participant.id,
                    "username": participant.username,
                    "nickname": participant.nickname,
                    "avatar_url": participant.avatar_url,
                    "bio": participant.bio if participant.show_bio else None,
                    "last_seen": participant.last_seen
                },
                "status": display_status,
                "last_message": {
                    "id": last_msg.id,
                    "sender_id": last_msg.sender_id,
                    "receiver_id": last_msg.receiver_id,
                    "content": last_msg.content,
                    "is_read": last_msg.is_read,
                    "is_edited": last_msg.is_edited,
                    "created_at": last_msg.created_at
                },
                "unread_count": unread_count
            })
        
        results.sort(key=lambda x: x["last_message"]["created_at"] if x["last_message"] else "", reverse=True)
        return results

    @transaction
    async def mark_messages_as_read(self, session: AsyncSession, receiver_id: int, sender_id: int):
        """
        Mark all messages from sender to receiver as read.
        """
        stmt = update(Message).where(
            Message.sender_id == sender_id,
            Message.receiver_id == receiver_id,
            Message.is_read == False
        ).values(is_read=True)
        await session.execute(stmt)

    @transaction
    async def delete_conversation(self, session: AsyncSession, user_id: int, other_id: int):
        """
        Logically delete conversation history for the current user.
        """
        # Sent messages by current user
        stmt_sent = update(Message).where(
            Message.sender_id == user_id,
            Message.receiver_id == other_id
        ).values(deleted_by_sender=True)
        
        # Received messages by current user
        stmt_recv = update(Message).where(
            Message.sender_id == other_id,
            Message.receiver_id == user_id
        ).values(deleted_by_receiver=True)
        
        await session.execute(stmt_sent)
        await session.execute(stmt_recv)


    @transaction
    async def update_privacy(self, session: AsyncSession, user_id: int, is_private: bool) -> bool:
        """
        Update user's privacy status.
        """
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            user.is_private = is_private
            return True
        return False

    _similarity_cooldown: dict = {}  # user_id -> last_run_timestamp

    async def recalculate_user_similarity(self, user_id: int):
        """
        Heavy operation: Re-calculates similarity between this user and all others.
        Throttled to run at most once every 5 minutes per user to avoid
        blocking the event loop on every /social/similar request.
        """
        import time as _time
        now = _time.time()
        last = self._similarity_cooldown.get(user_id, 0)
        if now - last < 300:  # 5-minute cooldown per user
            logger.info(f"Similarity recalc skipped for user {user_id} (cooldown)")
            return
        self._similarity_cooldown[user_id] = now

        if self.session:
            async with self.session() as session:
                # 1. Get current user's movies/genres
                user_stmt = select(Movies).where(Movies.user_id == user_id)
                user_res = await session.execute(user_stmt)
                user_movies = user_res.scalars().all()
                user_movie_ids = {m.tmdb_id for m in user_movies}
                user_genres = Counter()
                for m in user_movies:
                    if m.genre_ids:
                        user_genres.update(m.genre_ids.split(","))

                # 2. Get all other public users
                others_stmt = select(User.id).where(User.id != user_id, User.is_private == False, User.is_deleted == False)
                others_res = await session.execute(others_stmt)
                other_ids = others_res.scalars().all()

                if not other_ids:
                    logger.info("No other users found")
                    return

                # Fetch all movies for all other users in ONE query
                all_other_movies_stmt = select(Movies).where(Movies.user_id.in_(other_ids))
                all_other_movies_res = await session.execute(all_other_movies_stmt)
                all_other_movies = all_other_movies_res.scalars().all()

                # Group by user_id
                from collections import defaultdict
                movies_by_user = defaultdict(list)
                for m in all_other_movies:
                    movies_by_user[m.user_id].append(m)

                for other_id in other_ids:
                    other_movies = movies_by_user[other_id]
                    other_movie_ids = {m.tmdb_id for m in other_movies}
                    
                    # Shared movies score
                    shared_movies = user_movie_ids.intersection(other_movie_ids)
                    movie_score = len(shared_movies) * 0.2 # 5 shared movies = 1.0

                    # Shared genres score
                    other_genres = Counter()
                    for m in other_movies:
                        if m.genre_ids:
                            other_genres.update(m.genre_ids.split(","))
                    
                    # Simple Jaccard-like similarity for genres
                    common_genres = set(user_genres.keys()).intersection(set(other_genres.keys()))
                    genre_score = len(common_genres) * 0.1 # 10 shared genres = 1.0
                    
                    total_score = min(movie_score + genre_score, 1.0)
                    
                    if total_score > 0.1:
                        # Upsert similarity match
                        match_stmt = select(SimilarityMatch).where(SimilarityMatch.user_id == user_id, SimilarityMatch.target_id == other_id)
                        match_res = await session.execute(match_stmt)
                        match = match_res.scalar_one_or_none()

                        reasons = []

                        if shared_movies:
                            reasons.append(f"Both watched {len(shared_movies)} same films")
                        if common_genres:
                            reasons.append(f"Shared love for {len(common_genres)} genres")
                        if not match:
                            match = SimilarityMatch(user_id=user_id, target_id=other_id, score=total_score, reasons=", ".join(reasons))
                            session.add(match)
                        else:
                            match.score = total_score
                            match.reasons = ", ".join(reasons)

                await session.commit()

    @transaction
    async def get_profile(self, session: AsyncSession, user_id: int) -> dict:
        """
        Fetch public profile data for a user including top genres and favorite movies.
        """
        user_stmt   = select(User).where(User.id == user_id, User.is_deleted == False)
        user_result = await session.execute(user_stmt)
        user        = user_result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(str(user_id))
        # Get favorites
        fav_stmt = select(Movies).where(Movies.user_id == user.id, Movies.is_favorite == True).limit(3)
        fav_res = await session.execute(fav_stmt)
        
        favorites = [{
            "id":           m.id,
            "tmdb_id":      m.tmdb_id,
            "title":        m.title,
            "poster_url":   m.poster_url,
            "release_date": m.release_date
        } for m in fav_res.scalars().all()]

        # Get top genres
        movies_stmt = select(Movies.genre_ids).where(Movies.user_id == user.id)
        movies_res  = await session.execute(movies_stmt)
        genre_rows  = movies_res.scalars().all()
        genre_ids   = ",".join(genre_rows).strip(",")
        
        top_genres = []
        if genre_ids:
            ids = []
            for i in genre_ids.split(","):
                try:
                    ids.append(int(i.strip()))
                except ValueError:
                    continue
            
            if ids:
                count           = Counter(ids)
                top_genres      = [item for item, _ in count.most_common(3)]

        return {
            "id":           user.id,
            "username":     user.username,
            "nickname":     user.nickname,
            "avatar_url":   user.avatar_url,
            "bio":          user.bio if user.show_bio else None,
            "gender":       user.gender if user.show_gender else None,
            "age":          user.age if user.show_age else None,
            "location":     user.location if user.show_location else None,
            "created_at":   user.created_at,
            "last_seen":    user.last_seen,
            "favorites":    favorites if user.show_favorites else [],
            "top_genres":   top_genres if user.show_favorites else []
        }

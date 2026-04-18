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

from services.tmdb import fetch_tmdb_data
from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Integer,
    Boolean,
    select,
    delete,
    UniqueConstraint,
)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from fastapi.concurrency import run_in_threadpool
from functools import wraps
from typing import List, Optional
import logging
import bcrypt
from datetime import datetime, timezone
from collections import Counter
from dotenv import load_dotenv
from services.schemas import UserScheme

load_dotenv()

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
        super().__init__(f"Username {username} is reserved and cannot be registered.")


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

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="user", server_default="user")
    password: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # --- Device fingerprint (collected at signup) ---
    device: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    device_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    machine: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    os: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    memory: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hostname: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # --- Network / geolocation ---
    country: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # --- Account settings ---
    ai_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    max_toasts: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")

    # --- Account lifecycle ---
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(
        String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_seen: Mapped[str] = mapped_column(
        String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat()
    )

    movies: Mapped[List["Movies"]] = relationship("Movies", back_populates="user", lazy="selectin")


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

    __tablename__ = "movies"
    __table_args__ = (UniqueConstraint("user_id", "tmdb_id", name="uq_user_tmdb_movie"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    overview: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    genre_ids: Mapped[str] = mapped_column(String, nullable=False)  # Comma-separated TMDB genre IDs
    vote_average: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="Not yet")

    user: Mapped["User"] = relationship("User", back_populates="movies")
    watched_movies: Mapped[List["WatchedMovies"]] = relationship("WatchedMovies", back_populates="who_watched", lazy="selectin", cascade="all, delete-orphan")


class WatchedMovies(Base):
    """
    Records when a user marks a movie as 'Watched'.

    This is a separate table from Movies so that a user can track a movie
    (intent to watch) and later confirm they watched it, preserving both
    timestamps independently.
    """

    __tablename__ = "watched_movies"
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_user_watched_movie"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="Watched")
    watched_at: Mapped[str] = mapped_column(
        String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat()
    )

    who_watched: Mapped["Movies"] = relationship("Movies", back_populates="watched_movies")


# ---------------------------------------------------------------------------
# Global Constants
# ---------------------------------------------------------------------------
RESERVED_USERNAMES = {"admin", "root", "system", "superuser", "administrator"}


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

    def __init__(self, db_url: str, echo: bool = False):
        import sys
        from sqlalchemy.pool import NullPool
        # Use NullPool during testing to avoid asyncio event loop mismatch errors across test files
        poolclass = NullPool if "pytest" in sys.modules else None
        self.engine = create_async_engine(db_url, echo=echo, poolclass=poolclass)
        self.session = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create_tables(self):
        """Create all tables in the database (called once at startup)."""
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
            logger.info(f"Running function: {func.__name__}")
            async with self.session() as session:
                try:
                    result = await func(self, session, *args, **kwargs)
                    await session.commit()
                    logger.info(f"Done function: {func.__name__}")
                    return result
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Error in function: {func.__name__} - {str(e)}")
                    raise

        return wrapper

    # --- Queries ---

    async def user_exists(self, username: str) -> bool:
        """Check whether a user with the given username exists (non-deleted)."""
        async with self.session() as session:
            stmt = select(User).where(User.username == username)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return user is not None

    @transaction
    async def add_user(self, session: AsyncSession, user: UserScheme) -> bool:
        """
        Register a new user.

        Collects device and network metadata, hashes the password with
        bcrypt, and persists the record.

        Raises:
            UserAlreadyExists: If the username is already taken.
            ReservedUsernameError: If the username is in the reserved list.
        """
        if user.username.lower() in RESERVED_USERNAMES:
            raise ReservedUsernameError(user.username)

        hashed = await run_in_threadpool(bcrypt.hashpw, user.password.encode("utf-8"), bcrypt.gensalt())
        created_at = datetime.now(timezone.utc).isoformat()

        # Registration now always defaults to the 'user' role.
        # Admins must be seeded via environment variables or promoted by an existing admin.
        assigned_role = "user"

        new_user = User(
            username=user.username,
            role=assigned_role,
            password=hashed.decode("utf-8"),
            email=user.email,
            device="unknown",
            device_name="unknown",
            machine="unknown",
            os="unknown",
            memory="unknown",
            hostname="unknown",
            country="unknown",
            city="unknown",
            ip="unknown",
            ai_enabled=True,
            is_deleted=False,
            created_at=created_at,
            last_seen=created_at,
        )  # type: ignore

        is_user_exists = await self.user_exists(new_user.username)  # type: ignore
        if is_user_exists:
            logger.error(f"User already exists: {new_user.username}")
            raise UserAlreadyExists(new_user.username)  # type: ignore
        session.add(new_user)
        logger.info(f"Added user: {new_user.username} - {new_user.email}")
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
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(username)
        if hasattr(user, "is_deleted"):
            setattr(user, "is_deleted", True)
        logger.info(f"Deleted user: {user.username}")
        return True

    @transaction
    async def ensure_admin_exists(self, session: AsyncSession) -> None:
        """
        Ensures at least one admin exists in the system.

        Reads INITIAL_ADMIN_USERNAME, INITIAL_ADMIN_PASSWORD, and
        INITIAL_ADMIN_EMAIL from environment variables. If no user with the
        'admin' role exists, it creates one using these credentials.

        This is intended to be called at application startup.
        """
        stmt = select(User).where(User.role == "admin")
        result = await session.execute(stmt)
        admin_exists = result.scalar_one_or_none()
        if admin_exists:
            logger.info("Admin account already exists. Skipping seed.")
            return

        import os

        username = os.getenv("INITIAL_ADMIN_USERNAME")
        password = os.getenv("INITIAL_ADMIN_PASSWORD")
        email = os.getenv("INITIAL_ADMIN_EMAIL")

        if not username or not password or not email:
            logger.warning(
                "Initial admin credentials not fully provided in .env. "
                "Skipping superuser seeding."
            )
            return

        # Seed the superuser
        hashed = await run_in_threadpool(bcrypt.hashpw, password.encode("utf-8"), bcrypt.gensalt())
        created_at = datetime.now(timezone.utc).isoformat()

        new_admin = User(
            username=username,
            password=hashed.decode("utf-8"),
            email=email,
            role="admin",
            is_deleted=False,
            created_at=created_at,
            last_seen=created_at,
            city="System",
            country="System",
            ip="127.0.0.1",
            ai_enabled=True,
        )
        session.add(new_admin)
        logger.info(f"Successfully seeded superuser: {username}")

    @transaction
    async def get_user_by_username(self, session: AsyncSession, username: str) -> dict:
        """
        Retrieve a single user record by username.

        Returns:
            dict mapping column names to their values.

        Raises:
            UserNotFoundError: If no matching user is found.
        """
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(username)
        return {c.name: getattr(user, c.name) for c in user.__table__.columns}

    @transaction
    async def get_user_by_id(self, session: AsyncSession, id: int) -> dict:
        """
        Retrieve a single user record by primary key.

        Raises:
            UserNotFoundError: If no user with the given ID exists.
        """
        stmt = select(User).where(User.id == id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(str(id))
        return {c.name: getattr(user, c.name) for c in user.__table__.columns}

    @transaction
    async def get_all_users(self, session: AsyncSession, skip: int = 0, limit: int = 10) -> list[dict]:
        """
        Return a paginated list of all user records.

        Args:
            skip:  Number of rows to skip (offset).
            limit: Maximum number of rows to return.
        """
        stmt = select(User).offset(skip).limit(limit)
        result = await session.execute(stmt)
        users = result.scalars().all()
        return [
            {c.name: getattr(u, c.name) for c in u.__table__.columns} for u in users
        ]

    @transaction
    async def update_user_field(
        self, session: AsyncSession, username: str, field: str, value: str, current_password: Optional[str] = None
    ) -> bool:
        """
        Update a single field on a user record.

        Sensitive updates (password, email) require 'current_password' verification.
        Enforces a whitelist of allowed fields to prevent privilege escalation.

        Raises:
            UserNotFoundError: If the target user does not exist.
            ValueError: If an unauthorized field is requested or password verification fails.
        """
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(username)

        f_lower = field.lower()
        ALLOWED_FIELDS = {"password", "email", "ai_enabled", "username", "max_toasts"}
        
        if f_lower not in ALLOWED_FIELDS:
            logger.warning(f"Unauthorized update attempt on field '{field}' for user {username}")
            raise ValueError(f"Field '{field}' cannot be updated via this endpoint.")

        # Require password verification for sensitive changes
        if f_lower in {"password", "email"}:
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
            hashed = await run_in_threadpool(bcrypt.hashpw, value.encode("utf-8"), bcrypt.gensalt())
            setattr(user, "password", hashed.decode("utf-8"))
            return True

        if f_lower == "ai_enabled":
            bool_value = str(value).lower() in ("true", "1", "yes", "t")
            setattr(user, "ai_enabled", bool_value)
            return True

        if f_lower == "max_toasts":
            try:
                val = int(value)
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

        # For 'email', we just set it directly
        setattr(user, f_lower, value)
        logger.info(f"Updated user: {user.username} - {field}")
        return True


class MovieManager:
    """
    Encapsulates all movie-related database operations (async).

    Handles tracking, deletion, status updates, and genre-based
    recommendation lookups against the TMDB API.

    Args:
        db_url: PostgreSQL async connection URL.
        echo:   If True, SQLAlchemy will log all generated SQL.
    """

    def __init__(self, db_url: str, echo: bool = False) -> None:
        import sys
        from sqlalchemy.pool import NullPool
        poolclass = NullPool if "pytest" in sys.modules else None
        self.engine = create_async_engine(db_url, echo=echo, poolclass=poolclass)
        self.session = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

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
                    result = await func(self, session, *args, **kwargs)
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
        async with self.session() as session:
            stmt = (
                select(Movies.genre_ids)
                .join(User, User.id == Movies.user_id)
                .where(User.username == username)
            )
            result = await session.execute(stmt)
            genre_rows = result.scalars().all()
            
        genre_ids = ",".join(genre_rows)
        genre_ids = genre_ids.strip(",")
        if not genre_ids or genre_ids is None:
            logger.info(f"User {username} hasn't rated/watched enough categories yet.")
            return []
        ids = [int(i) for i in genre_ids.split(",")]
        count = Counter(ids)
        top_genres = [item for item, _ in count.most_common(5)]
        return top_genres

    @transaction
    async def get_watched_movies(
        self, session: AsyncSession, username: str, skip: int = 0, limit: int = 10
    ) -> list[dict]:
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
        user_stmt = select(User.id).where(User.username == username)
        user_result = await session.execute(user_stmt)
        user_row = user_result.scalar_one_or_none()
        if user_row is None:
            raise UserNotFoundError(username)

        # SQL-level pagination — only fetches the requested slice
        movies_stmt = (
            select(Movies)
            .where(Movies.user_id == user_row)
            .offset(skip)
            .limit(limit)
        )
        movies_result = await session.execute(movies_stmt)
        movies = movies_result.scalars().all()
        return [
            {c.name: getattr(m, c.name) for c in m.__table__.columns}
            for m in movies
        ]

    @transaction
    async def delete_movie(self, session: AsyncSession, username: str, movie_id: int) -> bool:
        """
        Remove a movie from a user's tracked collection by its database ID.

        Uses the primary key directly — no external API dependency required.

        Raises:
            UserNotFoundError:  If the user does not exist.
            MovieNotFoundError: If the movie is not in the user's list.
        """
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError(username)

        movie_stmt = select(Movies).where(
            Movies.id == movie_id, Movies.user_id == user.id
        )
        movie_result = await session.execute(movie_stmt)
        movie = movie_result.scalar_one_or_none()
        if not movie:
            raise MovieNotFoundError(str(movie_id))

        await session.delete(movie)
        logger.info(f"Deleted movie: {movie.title} (id={movie_id}) - {user.username}")
        return True

    async def update_status(self, username: str, status: str, query: str) -> bool:
        """
        Mark a tracked movie with a new status (e.g. 'Watched').

        Creates a WatchedMovies record with the current UTC timestamp.

        Raises:
            MovieNotFoundError: If the movie is not in the user's tracked list or TMDB fails.
            MovieAlreadyExists: If the movie already has a WatchedMovies entry.
            UserNotFoundError:  If the user does not exist.
        """
        data = await fetch_tmdb_data(query)
        if not data:
            raise MovieNotFoundError(query)

        async with self.session() as session:
            try:
                stmt = select(User).where(User.username == username)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                if not user:
                    raise UserNotFoundError(username)

                movie_stmt = select(Movies).where(
                    Movies.user_id == user.id, Movies.tmdb_id == data.get("tmdb_id")
                )
                movie_result = await session.execute(movie_stmt)
                movie = movie_result.scalar_one_or_none()
                if not movie:
                    raise MovieNotFoundError(data.get("title", query))

                # Update status on the tracked movie
                movie.status = status

                if status == "Watched":
                    # Check if already marked as watched
                    already_watched_stmt = select(WatchedMovies).where(
                        WatchedMovies.user_id == user.id, WatchedMovies.movie_id == movie.id
                    )
                    already_watched_result = await session.execute(already_watched_stmt)
                    if already_watched_result.scalar_one_or_none():
                        raise MovieAlreadyExists(movie.title)
                    
                    watched_entry = WatchedMovies(
                        user_id=user.id,
                        movie_id=movie.id,
                        title=movie.title,
                        status=status,
                        watched_at=datetime.now(timezone.utc).isoformat(),
                    )
                    session.add(watched_entry)
                else:
                    # If changed from Watched to something else, remove from WatchedMovies
                    await session.execute(
                        delete(WatchedMovies).where(
                            WatchedMovies.user_id == user.id, WatchedMovies.movie_id == movie.id
                        )
                    )

                await session.commit()
                return True
            except Exception:
                await session.rollback()
                raise

    async def add_movie(self, username: str, query: str) -> bool:
        """
        Search TMDB for a movie and add it to the user's tracked list.

        The query is forwarded to the TMDB search API; the top result
        is persisted with its metadata (genres, rating, overview).

        Raises:
            MovieAlreadyExists: If the movie is already tracked.
            UserNotFoundError:  If the user does not exist.
            MovieNotFoundError: If TMDB fails or returns no data.
        """
        data = await fetch_tmdb_data(query)
        if not data:
            raise MovieNotFoundError(query)

        async with self.session() as session:
            try:
                stmt = select(User).where(User.username == username)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                if not user:
                    raise UserNotFoundError(username)

                is_exist_stmt = select(Movies).where(
                    Movies.user_id == user.id, Movies.tmdb_id == data.get("tmdb_id")
                )
                is_exist_result = await session.execute(is_exist_stmt)
                is_exist = is_exist_result.scalar_one_or_none()
                if is_exist:
                    raise MovieAlreadyExists(data.get("title"))  # type:ignore
                if user and user is not None:
                    movie = Movies(
                        user_id=user.id,
                        tmdb_id=data.get("tmdb_id"),
                        title=data.get("title"),
                        overview=data.get("overview"),
                        genre_ids=data.get("genre_ids"),
                        status="Not yet",
                        vote_average=data.get("vote_average"),
                    )
                    session.add(movie)
                    await session.commit()
                    return True
                return False
            except Exception:
                await session.rollback()
                raise

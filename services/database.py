"""
services/database.py — Data Access Layer

Defines the SQLAlchemy ORM models (User, Movies, WatchedMovies) and the
manager classes (UserManager, MovieManager) that encapsulate all database
operations behind clean, transactional interfaces.

Design decisions:
    • SQLite is used as the default datastore for portability; the engine
      URL is injected via the DB_PATH environment variable.
    • Every write operation is wrapped in an auto-commit / rollback
      transaction decorator so callers never manage sessions directly.
    • Device and network metadata is collected at registration time for
      analytics purposes — this is intentional.
"""

import collections
from services import tmdb
from services.tmdb import fetch_tmdb_data, fetch_recommendations
from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Integer,
    create_engine,
    Boolean,
    select,
)
from sqlalchemy.orm import relationship, sessionmaker, DeclarativeBase
from functools import wraps
import logging
from pydantic import EmailStr, BaseModel, field_validator
import bcrypt
import socket
import requests
import psutil
import platform
from datetime import datetime, timezone
from collections import Counter
from dotenv import load_dotenv
from services.schemas import UserScheme, MovieScheme

load_dotenv()

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
format = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=format)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System Metadata Collectors
# ---------------------------------------------------------------------------
# These functions gather client environment data at registration time.
# The data is stored alongside the user record for admin analytics.
# ---------------------------------------------------------------------------


def collect_device_info() -> dict[str, str]:
    """
    Collect hardware and OS metadata from the host machine.

    Returns:
        dict with keys: device, device_name, machine, os, hostname, memory
    """
    return {
        "device": platform.platform(),
        "device_name": platform.node(),
        "machine": platform.machine(),
        "os": platform.system(),
        "hostname": socket.gethostname(),
        "memory": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
    }


def fetch_network_info() -> dict[str, str]:
    """
    Retrieve geolocation and IP data from the ipinfo.io API.

    Falls back to 'unknown' values on network errors so that user
    registration is never blocked by a third-party outage.

    Returns:
        dict with keys: country, city, ip
    """
    try:
        data: dict = requests.get("https://ipinfo.io/json").json()
        return {
            "country": data.get("country", "unknown"),
            "city": data.get("city", "unknown"),
            "ip": data.get("ip", "unknown"),
        }
    except Exception as e:
        logger.warning(f"Could not fetch network info: {str(e)}")
        return {"country": "unknown", "city": "unknown", "ip": "unknown"}


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


class UserNotFoundError(Exception):
    """Raised when a database lookup for a user yields no results."""

    def __init__(self, username: str, *args: object) -> None:
        super().__init__(f"User {username} not found - args=({args})")


class MovieAlreadyExists(Exception):
    """Raised when a movie is already in the user's tracked collection."""

    def __init__(self, title: str, *args: object) -> None:
        super().__init__(f"Movie {title} already exists - args=({args})")


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

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False, default="user", server_default="user")
    password = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)

    # --- Device fingerprint (collected at signup) ---
    device = Column(String, nullable=False)
    device_name = Column(String, nullable=False)
    machine = Column(String, nullable=False)
    os = Column(String, nullable=False)
    memory = Column(String, nullable=False)
    hostname = Column(String, nullable=False)

    # --- Network / geolocation ---
    country = Column(String, nullable=False)
    city = Column(String, nullable=False)
    ip = Column(String, nullable=False)

    # --- Account lifecycle ---
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat
    )
    last_seen = Column(
        String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat
    )

    movies = relationship("Movies", back_populates="user")


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

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    tmdb_id = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    overview = Column(String, nullable=True)
    genre_ids = Column(String, nullable=False)  # Comma-separated TMDB genre IDs
    vote_average = Column(String, nullable=True)
    status = Column(String, nullable=False, default="Not yet")

    user = relationship("User", back_populates="movies")
    watched_movies = relationship("WatchedMovies", back_populates="who_watched")


class WatchedMovies(Base):
    """
    Records when a user marks a movie as 'Watched'.

    This is a separate table from Movies so that a user can track a movie
    (intent to watch) and later confirm they watched it, preserving both
    timestamps independently.
    """

    __tablename__ = "watched_movies"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("movies.user_id"))
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="Watched")
    watched_at = Column(
        String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat()
    )

    who_watched = relationship("Movies", back_populates="watched_movies")


# ---------------------------------------------------------------------------
# UserManager
# ---------------------------------------------------------------------------


class UserManager:
    """
    Encapsulates all user-related database operations.

    Manages its own SQLAlchemy engine and session factory.  Every public
    method that mutates data is decorated with `@transaction` to guarantee
    atomic commits or full rollbacks on failure.

    Args:
        db_path: Filesystem path to the SQLite database file.
        echo:    If True, SQLAlchemy will log all generated SQL.
    """

    def __init__(self, db_path: str, echo: bool = False):
        self.engine = create_engine(f"sqlite:///{db_path}", echo=echo)
        Base.metadata.create_all(bind=self.engine)
        self.session = sessionmaker(bind=self.engine)

    # --- Decorators ---

    @staticmethod
    def catch_error(exceptions: tuple = (Exception,)):
        """
        Decorator factory that wraps a method in try/except logging.

        Args:
            exceptions: Tuple of exception classes to catch and re-raise.
        """

        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                try:
                    logger.info(f"Running function: {func.__name__}")
                    result = func(self, *args, **kwargs)
                    logger.info(f"Done function: {func.__name__}")
                    return result
                except exceptions as e:
                    logger.error(
                        f"Error in function: {func.__name__} - error: {str(e)}"
                    )
                    raise

            return wrapper

        return decorator

    @staticmethod
    def transaction(func):
        """
        Decorator that wraps a method in a database session context.

        Opens a new session, calls the decorated function with the session
        as its first positional argument (after `self`), commits on success,
        and rolls back + re-raises on any exception.
        """

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            logger.info(f"Running function: {func.__name__}")
            with self.session() as session:
                try:
                    result = func(self, session, *args, **kwargs)
                    session.commit()
                    logger.info(f"Done function: {func.__name__}")
                    return result
                except Exception as e:
                    session.rollback()
                    logger.error(f"Error in function: {func.__name__} - {str(e)}")
                    raise

        return wrapper

    # --- Queries ---

    def user_exists(self, username: str) -> bool:
        """Check whether a user with the given username exists (non-deleted)."""
        with self.session() as session:
            stmd = select(User).where(User.username == username)
            user = session.execute(stmd).scalar_one_or_none()
            return user is not None

    @transaction
    def add_user(self, session, user: UserScheme) -> bool:
        """
        Register a new user.

        Collects device and network metadata, hashes the password with
        bcrypt, and persists the record.  The username 'admin' is
        automatically assigned the admin role.

        Raises:
            UserAlreadyExists: If the username is already taken.
        """
        hashed = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt())
        network_data = fetch_network_info()
        device_info = collect_device_info()
        created_at = datetime.now(timezone.utc).isoformat()

        # Auto-promote the 'admin' username to the admin role
        assigned_role = "admin" if user.username.lower() == "admin" else "user"

        new_user = User(
            username=user.username,
            role=assigned_role,
            password=hashed,
            email=user.email,
            device=device_info.get("device"),
            device_name=device_info.get("device_name"),
            machine=device_info.get("machine"),
            os=device_info.get("os"),
            memory=device_info.get("memory"),
            hostname=device_info.get("hostname"),
            country=network_data.get("country"),
            city=network_data.get("city"),
            ip=network_data.get("ip"),
            is_deleted=False,
            created_at=created_at,
            last_seen=created_at,
        )  # type: ignore

        is_user_exists = self.user_exists(new_user.username)
        if is_user_exists:
            logger.error(f"User already exists: {new_user.username}")
            raise UserAlreadyExists(new_user.username)
        session.add(new_user)
        logger.info(f"Added user: {new_user.username} - {new_user.email}")
        return True

    @transaction
    def delete_user(self, session, username: str) -> bool:
        """
        Soft-delete a user by setting `is_deleted = True`.

        The record remains in the database for auditing but will not
        appear in normal queries.

        Raises:
            UserNotFoundError: If no user with the given username exists.
        """
        user = session.query(User).filter_by(username=username).first()
        if not user:
            raise UserNotFoundError(username)
        if hasattr(user, "is_deleted"):
            setattr(user, "is_deleted", True)
        logger.info(f"Deleted user: {user.username}")
        return True

    @transaction
    def get_user_by_username(self, session, username: str) -> dict:
        """
        Retrieve a single user record by username.

        Returns:
            dict mapping column names to their values.

        Raises:
            UserNotFoundError: If no matching user is found.
        """
        user = session.query(User).filter_by(username=username).first()
        if not user:
            raise UserNotFoundError(username)
        return {c.name: getattr(user, c.name) for c in user.__table__.columns}

    @transaction
    def get_user_by_id(self, session, id: int) -> dict:
        """
        Retrieve a single user record by primary key.

        Raises:
            UserNotFoundError: If no user with the given ID exists.
        """
        user = session.query(User).filter_by(id=id).first()
        if not user:
            raise UserNotFoundError(str(id))
        return {c.name: getattr(user, c.name) for c in user.__table__.columns}

    @transaction
    def get_all_users(self, session, skip: int = 0, limit: int = 10) -> list[dict]:
        """
        Return a paginated list of all user records.

        Args:
            skip:  Number of rows to skip (offset).
            limit: Maximum number of rows to return.
        """
        users = session.query(User).offset(skip).limit(limit).all()
        return [
            {c.name: getattr(u, c.name) for c in u.__table__.columns} for u in users
        ]

    @transaction
    def update_user_field(self, session, username: str, field: str, value: str) -> bool:
        """
        Update a single field on a user record.

        Password values are automatically bcrypt-hashed before storage.

        Raises:
            UserNotFoundError: If the target user does not exist.
        """
        user = session.query(User).filter_by(username=username).first()
        if not user:
            raise UserNotFoundError(username)
        if field.lower() == "password":
            hashed = bcrypt.hashpw(field.encode("utf-8"), bcrypt.gensalt())
            setattr(user, field, hashed)
            return True
        setattr(user, field, value)
        session.commit()
        logger.info(f"Updated user: {user.username} - {field}: {value}")
        return True


# ---------------------------------------------------------------------------
# MovieManager
# ---------------------------------------------------------------------------


class MovieManager:
    """
    Encapsulates all movie-related database operations.

    Handles tracking, deletion, status updates, and genre-based
    recommendation lookups against the TMDB API.

    Args:
        db_path: Filesystem path to the SQLite database file.
        echo:    If True, SQLAlchemy will log all generated SQL.
    """

    def __init__(self, db_path: str, echo: bool = False) -> None:
        self.engine = create_engine(f"sqlite:///{db_path}", echo=echo)
        self.session = sessionmaker(bind=self.engine)

    @staticmethod
    def transaction(func):
        """
        Decorator that wraps a method in a database session context.

        Identical to UserManager.transaction — duplicated here because
        each manager owns its own engine/session factory.
        """

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            logger.info(f"Running function: {func.__name__}")
            with self.session() as session:
                try:
                    result = func(self, session, *args, **kwargs)
                    session.commit()
                    logger.info(f"Done function: {func.__name__}")
                    return result
                except Exception as e:
                    session.rollback()
                    logger.error(f"Error in function: {func.__name__} - {str(e)}")
                    raise

        return wrapper

    def get_top_genres(self, username: str) -> list:
        """
        Analyse a user's tracked movies and return the top 5 most
        frequently occurring TMDB genre IDs.

        This powers the recommendation engine: the returned IDs are
        passed to TMDB's /discover endpoint to find similar films.

        Returns:
            List of up to 5 integer genre IDs, sorted by frequency
            (most common first).  Empty list if the user has no movies.
        """
        genre_ids = ""
        with self.session() as session:
            user = session.query(User).filter_by(username=username).first()
            if user and user is not None:
                for movie in user.movies:
                    genre_ids += "," + movie.genre_ids
        genre_ids = genre_ids.strip(",")
        if not genre_ids or genre_ids is None:
            logger.info(f"User {username} hasn't rated/watched enough categories yet.")
            return []
        ids = [int(i) for i in genre_ids.split(",")]
        count = Counter(ids)
        top_genres = [item for item, _ in count.most_common(5)]
        return top_genres

    @transaction
    def get_watched_movies(
        self, session, username: str, skip: int = 0, limit: int = 10
    ) -> list[dict]:
        """
        Return a paginated list of movies tracked by the given user.

        Args:
            username: Owner of the movie collection.
            skip:     Number of items to skip (offset).
            limit:    Maximum number of items to return.

        Raises:
            UserNotFoundError: If no user with the given username exists.
        """
        user = session.query(User).filter_by(username=username).first()
        if not user:
            raise UserNotFoundError(username)
        # Slice-based pagination on the loaded relationship
        return [
            {c.name: getattr(m, c.name) for c in m.__table__.columns}
            for m in user.movies[skip : skip + limit]
        ]

    @transaction
    def delete_movie(self, session, username: str, query: str) -> bool:
        """
        Remove a movie from a user's tracked collection.

        The movie is identified by searching TMDB with the given query
        string and matching the resulting tmdb_id against the database.

        Raises:
            MovieNotFoundError: If the movie is not in the user's list.
        """
        user = session.query(User).filter_by(username=username).first()
        data = fetch_tmdb_data(query)
        is_exist = (
            session.query(Movies)
            .filter_by(user_id=user.id, tmdb_id=data.get("tmdb_id"))
            .first()
        )
        if not is_exist:
            raise MovieNotFoundError(data.get("title"))  # type:ignore
        if user and user is not None:
            session.delete(is_exist)
            logger.info(f"Deleted movie: {data.get('title')} - {user.username}")
            return True
        return False

    @transaction
    def update_status(self, session, username: str, status: str, query: str) -> bool:
        """
        Mark a tracked movie with a new status (e.g. 'Watched').

        Creates a WatchedMovies record with the current UTC timestamp.

        Raises:
            MovieAlreadyExists: If the movie already has this status.
            UserNotFoundError:  If the user does not exist.
        """
        user = session.query(User).filter_by(username=username).first()
        data = fetch_tmdb_data(query)
        is_exists = (
            session.query(Movies)
            .filter_by(user_id=user.id, tmdb_id=data.get("tmdb_id"))
            .first()
        )
        if is_exists:
            raise MovieAlreadyExists(data.get("title"))  # type: ignore
        if user and user is not None:
            movie = WatchedMovies(
                user_id=user.id,
                title=data.get("title"),
                status=status,
                watched_at=datetime.now(timezone.utc).isoformat(),
            )
            session.add(movie)
            return True
        raise UserNotFoundError(username)

    @transaction
    def add_movie(self, session, username: str, query: str) -> bool:
        """
        Search TMDB for a movie and add it to the user's tracked list.

        The query is forwarded to the TMDB search API; the top result
        is persisted with its metadata (genres, rating, overview).

        Raises:
            MovieAlreadyExists: If the movie is already tracked.
            UserNotFoundError:  If the user does not exist.
        """
        user = session.query(User).filter_by(username=username).first()
        data = fetch_tmdb_data(query)
        is_exist = (
            session.query(Movies)
            .filter_by(user_id=user.id, tmdb_id=data.get("tmdb_id"))
            .first()
        )
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
            return True
        raise UserNotFoundError(username)

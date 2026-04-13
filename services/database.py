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

format = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=format)
logger = logging.getLogger(__name__)


def collect_device_info() -> dict[str, str]:
    return {
        "device": platform.platform(),
        "device_name": platform.node(),
        "machine": platform.machine(),
        "os": platform.system(),
        "hostname": socket.gethostname(),
        "memory": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
    }


def fetch_network_info() -> dict[str, str]:
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


class Base(DeclarativeBase):
    pass


class UserAlreadyExists(Exception):
    def __init__(self, username: str, *args: object) -> None:
        super().__init__(f"User {username} already exists - args=({args})")


class UserNotFoundError(Exception):
    def __init__(self, username: str, *args: object) -> None:
        super().__init__(f"User {username} not found - args=({args})")


class MovieAlreadyExists(Exception):
    def __init__(self, title: str, *args: object) -> None:
        super().__init__(f"Movie {title} already exists - args=({args})")





class User(Base):
    """
    Well.. You might ask, 'Why are you collecting so much data?'
    the answer? idk either.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    device = Column(String, nullable=False)
    device_name = Column(String, nullable=False)
    machine = Column(String, nullable=False)
    os = Column(String, nullable=False)
    memory = Column(String, nullable=False)
    hostname = Column(String, nullable=False)
    country = Column(String, nullable=False)
    city = Column(String, nullable=False)
    ip = Column(String, nullable=False)

    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat
    )
    last_seen = Column(
        String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat
    )
    movies = relationship("Movies", back_populates="user")


class Movies(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    tmdb_id = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    overview = Column(String, nullable=True)
    genre_ids = Column(String, nullable=False)
    vote_average = Column(String, nullable=True)
    status = Column(String, nullable=False, default="Not yet")
    # watched_at = Column(
    #    String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat()
    # )
    user = relationship("User", back_populates="movies")
    watched_movies = relationship("WatchedMovies", back_populates="who_watched")


class WatchedMovies(Base):
    __tablename__ = "watched_movies"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("movies.user_id"))
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="Watched")
    watched_at = Column(
        String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat()
    )
    who_watched = relationship("Movies", back_populates="watched_movies")


class UserManager:
    def __init__(self, db_path: str, echo: bool = False):
        self.engine = create_engine(f"sqlite:///{db_path}", echo=echo)
        Base.metadata.create_all(bind=self.engine)
        self.session = sessionmaker(bind=self.engine)

    @staticmethod
    def catch_error(exceptions: tuple = (Exception,)):
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

    def user_exists(self, username: str) -> bool:
        with self.session() as session:
            stmd = select(User).where(User.username == username)
            user = session.execute(stmd).scalar_one_or_none()
            return user is not None

    @transaction
    def add_user(self, session, user: UserScheme) -> bool:
        hashed = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt())
        network_data = fetch_network_info()
        device_info = collect_device_info()
        created_at = datetime.now(timezone.utc).isoformat()

        user = User(
            username=user.username,
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

        is_user_exists = self.user_exists(user.username)
        if is_user_exists:
            logger.error(f"User already exists: {user.username}")
            raise UserAlreadyExists(user.username)
        session.add(user)
        logger.info(f"Added user: {user.username} - {user.email}")
        return True

    @transaction
    def delete_user(self, session, username: str) -> bool:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            raise UserNotFoundError(username)
        if hasattr(user, "is_deleted"):
            setattr(user, "is_deleted", True)
        logger.info(f"Deleted user: {user.username}")
        return True

    @transaction
    def get_user_by_username(self, session, username: str) -> dict:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            raise UserNotFoundError(username)
        return {c.name: getattr(user, c.name) for c in user.__table__.columns}

    @transaction
    def get_user_by_id(self, session, id: int) -> dict:
        user = session.query(User).filter_by(id=id).first()
        if not user:
            raise UserNotFoundError(str(id))
        return {c.name: getattr(user, c.name) for c in user.__table__.columns}

    @transaction
    def get_all_users(self, session, skip: int = 0, limit: int = 10) -> list[dict]:
        users = session.query(User).offset(skip).limit(limit).all()
        return [
            {c.name: getattr(u, c.name) for c in u.__table__.columns} for u in users
        ]

    @transaction
    def update_user_field(self, session, username: str, field: str, value: str) -> bool:
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


class MovieManager:
    def __init__(self, db_path: str, echo: bool = False) -> None:
        self.engine = create_engine(f"sqlite:///{db_path}", echo=echo)
        self.session = sessionmaker(bind=self.engine)

    @staticmethod
    def transaction(func):
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
    def get_watched_movies(self, session, username: str, skip: int = 0, limit: int = 10) -> list[dict]:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            raise UserNotFoundError(username)
        # Use simple slice-based pagination for relationships (though query filter is better, this works for existing list structure)
        return [
            {c.name: getattr(m, c.name) for c in m.__table__.columns}
            for m in user.movies[skip:skip+limit]
        ]

    @transaction
    def delete_movie(self, session, username: str, query: str) -> bool:
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

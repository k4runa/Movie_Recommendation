import os
from services.database import UserManager, MovieManager
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)
load_dotenv()

DB_PATH = os.getenv("DB_PATH", "database/database.db")
if not DB_PATH:
    logger.error("FATAL: DB_PATH not found.")
    raise ValueError("FATAL: DB_PATH not found. Please set in .env")

dir_path = os.path.dirname(DB_PATH)
if dir_path:
    os.makedirs(dir_path, exist_ok=True)

users_manager = UserManager(db_path=DB_PATH, echo=False)  # type:ignore
movies_manager = MovieManager(db_path=DB_PATH, echo=False)  # type:ignore

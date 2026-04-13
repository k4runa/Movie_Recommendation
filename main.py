from services.database import (
    UserManager,
    MovieManager,
    logger,
    UserAlreadyExists,
    UserNotFoundError,
    MovieAlreadyExists,
)
from services.schemas import (
    UserScheme, 
    MovieScheme, 
    APIResponseUser, 
    APIResponseUsersList, 
    APIResponseWatchedMoviesList
)
from services.tmdb import fetch_recommendations
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordRequestForm
from services.auth import verify_password, create_access_token, get_current_user
import os
from dotenv import load_dotenv
from functools import wraps
from pydantic import BaseModel

load_dotenv()

DB_PATH = os.getenv("DB_PATH")
if not DB_PATH:
    logger.error(f"FATAL: DB_PATH not found.")
    raise ValueError("FATAL: DB_PATH not found. Please set in .env")

dir_path = os.path.dirname(DB_PATH)
if dir_path:
    os.makedirs(dir_path, exist_ok=True)

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    logger.warning("API_KEY not set")
app = FastAPI()


users = UserManager(db_path=DB_PATH, echo=False)  # type:ignore
movies = MovieManager(db_path=DB_PATH, echo=False)  # type:ignore


class UpdateUserRequest(BaseModel):
    field: str
    value: str


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    logger.info(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(UserNotFoundError)
async def user_not_found_handler(request: Request, exc: UserNotFoundError):
    logger.warning(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=404, content={"detail": "User not found"})


@app.exception_handler(UserAlreadyExists)
async def user_exists_handler(request: Request, exc: UserAlreadyExists):
    logger.warning(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=409, content={"detail": "User already exists."})


@app.exception_handler(MovieAlreadyExists)
async def movie_exists_handler(request: Request, exc: MovieAlreadyExists):
    logger.warning(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=409, content={"detail": "Movie already exists"})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def print_log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"running function: {func.__name__}")
        result = func(*args, **kwargs)
        logger.info(f"done function: {func.__name__}")
        return result

    return wrapper


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user_in_db = users.get_user_by_username(form_data.username) # type: ignore
    except UserNotFoundError:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    if not verify_password(form_data.password, user_in_db.get("password", "")):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
        
    access_token = create_access_token(data={"sub": user_in_db["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


@print_log
@app.post("/users")
def register(user: UserScheme):
    users.add_user(user)  # type:ignore
    return {"success": True, "message": "User successfully added."}


@print_log
@app.get("/users", response_model=APIResponseUsersList)
def get_all_users():
    logger.info("Fetching all users from database...")
    all_users = users.get_all_users()  # type: ignore
    logger.info("Fetched all users")
    return {"success": True, "data": {"users": all_users}}


@print_log
@app.get("/users/id/{id}", response_model=APIResponseUser)
def get_user_by_id(id: int):
    user = users.get_user_by_id(id)  # type: ignore
    return {"success": True, "data": {"user": user}}


@print_log
@app.get("/users/{username}", response_model=APIResponseUser)
def get_user_by_username(username: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("username") != username:
         raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    user = users.get_user_by_username(username)  # type: ignore
    return {"success": True, "data": {"user": user}}


@print_log
@app.delete("/users/{username}")
def delete_user(username: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("username") != username:
         raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    success = users.delete_user(username)  # type: ignore
    return {"success": success}


@print_log
@app.patch("/users/{username}")
def update_user_field(username: str, v: UpdateUserRequest, current_user: dict = Depends(get_current_user)):
    if current_user.get("username") != username:
         raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    success = users.update_user_field(username, v.field, v.value)  # type: ignore
    return {"success": success}


@print_log
@app.get("/movies/{username}/watched", response_model=APIResponseWatchedMoviesList)
def get_watched_movies(username: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("username") != username:
         raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    watched_movies = movies.get_watched_movies(username)  # type: ignore
    return {"success": True, "data": {"watched_movies": watched_movies}}


@print_log
@app.delete("/movies/{username}/{title}")
def delete_movie(username: str, title: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("username") != username:
         raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    success = movies.delete_movie(username, title)  # type: ignore
    return {"success": success}


@print_log
@app.post("/movies/{username}")
def add_movie(username: str, movie: MovieScheme, current_user: dict = Depends(get_current_user)):
    if current_user.get("username") != username:
         raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    movies.add_movie(username=username, query=movie.query)  # type: ignore
    return {"success": True, "message": "Movie successfully added."}


@print_log
@app.get("/movies/recommendations/{username}")
def get_recommendations(username: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("username") != username:
         raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    recommendations = fetch_recommendations(movies.get_top_genres(username))
    return {"success": True, "data": {"recommendations": recommendations}}

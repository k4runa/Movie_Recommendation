from fastapi import APIRouter, Depends, HTTPException
from services.schemas import MovieScheme, APIResponseWatchedMoviesList
from services.deps import movies_manager
from services.database import logger
from services.auth import get_current_user
from services.tmdb import fetch_recommendations
from functools import wraps

router = APIRouter(prefix="/movies", tags=["movies"])

def print_log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"running function: {func.__name__}")
        result = func(*args, **kwargs)
        logger.info(f"done function: {func.__name__}")
        return result
    return wrapper

@router.get("/{username}/watched", response_model=APIResponseWatchedMoviesList)
@print_log
def get_watched_movies(username: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("username") != username:
         raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    watched_movies = movies_manager.get_watched_movies(username)  # type: ignore
    return {"success": True, "data": {"watched_movies": watched_movies}}

@router.delete("/{username}/{title}")
@print_log
def delete_movie(username: str, title: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("username") != username:
         raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    success = movies_manager.delete_movie(username, title)  # type: ignore
    return {"success": success}

@router.post("/{username}")
@print_log
def add_movie(username: str, movie: MovieScheme, current_user: dict = Depends(get_current_user)):
    if current_user.get("username") != username:
         raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    movies_manager.add_movie(username=username, query=movie.query)  # type: ignore
    return {"success": True, "message": "Movie successfully added."}

@router.get("/recommendations/{username}")
@print_log
def get_recommendations(username: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("username") != username:
         raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    recommendations = fetch_recommendations(movies_manager.get_top_genres(username))
    return {"success": True, "data": {"recommendations": recommendations}}

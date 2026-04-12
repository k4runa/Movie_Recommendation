from services.database import UserManager,MovieManager,MovieScheme,UserScheme,logger,UserAlreadyExists,UserNotFoundError,MovieAlreadyExists
from services.tmdb import fetch_recommendations
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import os 
from dotenv import load_dotenv
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

users = UserManager(db_path=DB_PATH,echo=False)     #type:ignore
movies = MovieManager(db_path=DB_PATH,echo=False)   #type:ignore

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    logger.info(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

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
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

@app.post("/users")
def register(user:UserScheme):
    users.add_user(user) #type:ignore
    return {"success": True ,"message": {"User successfully added."}}

@app.post("/movies/{username}")
def add_movie(username: str, movie: MovieScheme):
    movies.add_movie(username=username, query=movie.query)  #type: ignore
    return {"success": True, "message": "Movie successfully added."}

@app.get("/movies/recommendations/{username}")
def get_recommendations(username: str):
    top_genres = movies.get_top_genres(username)
    recommendations = fetch_recommendations(top_genres)
    return {"success": True, "data": {"recommendations": recommendations}}

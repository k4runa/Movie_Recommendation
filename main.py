from services.database import User,UserManager,Watched,MovieManager,MovieScheme,UserScheme,logger
from services.tmdb import fetch_recommendations,fetch_tmdb_data
from fastapi import FastAPI
from pydantic import BaseModel
import os 
from dotenv import load_dotenv
load_dotenv()

DB_PATH = os.getenv("DB_PATH")
API_KEY = os.getenv("API_KEY")
os.makedirs(os.path.dirname(str(DB_PATH)),exist_ok=True)
app = FastAPI()

users = UserManager(db_path=DB_PATH,echo=False)     #type:ignore
movies = MovieManager(db_path=DB_PATH,echo=False)   #type:ignore
@app.post("/users")
def register(user:UserScheme):
    users.add_user(user) #type:ignore
    return {"success"}

@app.post("/movies/{username}")
def add_movie(username: str, movie: MovieScheme):
    movies.add_movie(username=username, query=movie.query)  #type: ignore
    return {"success": True}

@app.get("/movies/recommendations/{username}")
def get_recommendations(username: str):
    top_genres = movies.get_top_genres(username)
    recommendations = fetch_recommendations(top_genres)
    return {"recommendations": recommendations}

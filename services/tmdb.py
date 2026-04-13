import os
from typing import Any
import requests
from collections import Counter
from dotenv import load_dotenv
from sqlalchemy.engine import result

load_dotenv()


def fetch_tmdb_data(query: str) -> dict[str, Any]:
    api_key = os.getenv("API_KEY")
    response: dict = requests.get(
        f"https://api.themoviedb.org/3/search/movie?query={query}&api_key={api_key}"
    ).json()
    data = response.get("results", [])
    if not data:
        return {}
    movie = data[0]
    return {
        "tmdb_id": movie["id"],
        "title": movie["title"],
        "overview": movie["overview"],
        "genre_ids": ",".join(str(g) for g in movie["genre_ids"]),
        "vote_average": movie["vote_average"],
    }


def fetch_recommendations(genre_ids: list[int], limit: int = 5) -> list[dict[str, Any]]:
    """
    args:
        limit = fetchs first limit recommendations
        genre_ids = generated ids
    """
    if limit < 0:
        raise ValueError("Limit can not be negative.")
    if limit > 20:
        raise ValueError("Limit should be less than 20")
    api_key = os.getenv("API_KEY")
    genre_ids = ",".join(str(i) for i in genre_ids)  # type: ignore
    response = requests.get(
        f"https://api.themoviedb.org/3/discover/movie?with_genres={genre_ids}&api_key={api_key}"
    ).json()
    return [
        {
            "tmdb_id": m["id"],
            "title": m["title"],
            "vote_average": m["vote_average"],
            "overview": m["overview"],
        }
        for m in response["results"][:limit]
    ]

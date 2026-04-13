"""
services/tmdb.py — TMDB API Integration
=========================================
Provides functions to search for movies and discover recommendations
via The Movie Database (TMDB) REST API.

All functions read the API key from the API_KEY environment variable.
TMDB docs: https://developer.themoviedb.org/reference/intro/getting-started

Key endpoints used:
    • /3/search/movie   — title-based search (used by `fetch_tmdb_data`).
    • /3/discover/movie — genre-based discovery (used by `fetch_recommendations`).
"""

import os
from typing import Any
import requests
from collections import Counter
from dotenv import load_dotenv

load_dotenv()


def fetch_tmdb_data(query: str) -> dict[str, Any]:
    """
    Search TMDB for a movie by title and return the top result's metadata.

    Args:
        query: Free-text search string (e.g. "Inception", "The Matrix").

    Returns:
        dict with keys: tmdb_id, title, overview, genre_ids, vote_average.
        Empty dict if no results are found.
    """
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
    Discover movies matching the given genre IDs via TMDB's /discover endpoint.

    Results are sorted by TMDB's default popularity ranking.  The caller
    is responsible for filtering out movies the user already owns.

    Args:
        genre_ids: List of TMDB genre ID integers (e.g. [28, 878]).
        limit:     Maximum number of results to return (1–20).

    Returns:
        List of dicts, each containing: tmdb_id, title, vote_average, overview.

    Raises:
        ValueError: If limit is negative or exceeds 20.
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

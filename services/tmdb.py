import httpx
import os
import asyncio
import random
import logging
from typing import Any, List, Dict
from dotenv import load_dotenv
from services.cache import cache_service
from functools import wraps

load_dotenv()
logger = logging.getLogger(__name__)


def with_retries(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
    """
    Decorator that adds exponential backoff with jitter to async functions.
    Catches httpx network errors and retries before giving up.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
                    if attempt == max_retries - 1:
                        logger.error(f"{func.__name__} failed after {max_retries} attempts: {e}")
                        return [] if "search" in func.__name__ or "fetch_" in func.__name__ else {}
                    
                    # Exponential backoff with jitter
                    sleep_time = min(delay * (2 ** attempt) + random.uniform(0, 0.5), max_delay)
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {sleep_time:.2f}s...")
                    await asyncio.sleep(sleep_time)
            return [] if "search" in func.__name__ or "fetch_" in func.__name__ else {}
        return wrapper
    return decorator


async def fetch_tmdb_data(query: str) -> dict[str, Any]:
    """
    Search TMDB for a movie by title and return the top result's metadata.
    """
    results = await search_tmdb_movies(query, limit=1)
    return results[0] if results else {}


@with_retries()
async def _do_search_tmdb(query: str, limit: int) -> list[dict[str, Any]]:
    api_key = os.getenv("API_KEY")
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(
            f"https://api.themoviedb.org/3/search/movie?query={query}&api_key={api_key}"
        )
        response.raise_for_status()
        data_response: dict = response.json()
        
    results = data_response.get("results", [])
    return [
        {
            "tmdb_id": m["id"],
            "title": m.get("title", ""),
            "overview": m.get("overview", ""),
            "genre_ids": ",".join(str(g) for g in m.get("genre_ids", [])),
            "vote_average": str(m.get("vote_average", 0)),
            "poster_url": f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get("poster_path") else "",
            "release_date": m.get("release_date", ""),
        }
        for m in results[:limit]
    ]

async def search_tmdb_movies(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Search TMDB for movies by title and return a list of results.
    """
    if not query:
        return []

    cache_key = f"tmdb_search_{query}_{limit}"
    return await cache_service.get_or_fetch(cache_key, _do_search_tmdb, ttl=3600, query=query, limit=limit)


@with_retries()
async def fetch_tmdb_movie_by_id(tmdb_id: int) -> dict[str, Any]:
    """
    Fetch full metadata for a specific movie by its TMDB ID.
    """
    api_key = os.getenv("API_KEY")
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(
            f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={api_key}"
        )
        response.raise_for_status()
        movie = response.json()
        
    return {
        "tmdb_id": movie["id"],
        "title": movie["title"],
        "overview": movie.get("overview", ""),
        "genre_ids": ",".join(str(g["id"]) for g in movie.get("genres", [])),
        "vote_average": str(movie.get("vote_average", 0)),
        "poster_url": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else "",
        "release_date": movie.get("release_date", ""),
    }


@with_retries()
async def _do_fetch_recommendations(genre_str: str, limit: int, page: int, sort_by: str) -> List[Dict[str, Any]]:
    api_key = os.getenv("API_KEY")
    async with httpx.AsyncClient(timeout=5.0) as client:
        url = f"https://api.themoviedb.org/3/discover/movie?with_genres={genre_str}&api_key={api_key}&page={page}&sort_by={sort_by}"
        response = await client.get(url)
        response.raise_for_status()
        response_data = response.json()
        
        return [
            {
                "tmdb_id": m["id"],
                "title": m.get("title", ""),
                "overview": m.get("overview", ""),
                "vote_average": str(m.get("vote_average", 0)),
                "poster_url": f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get("poster_path") else "",
                "release_date": m.get("release_date", ""),
                "genre_ids": m.get("genre_ids", [])
            }
            for m in response_data.get("results", [])[:limit]
        ]

async def fetch_recommendations(
    genre_ids: List[int], limit: int = 20, page: int = 1, sort_by: str = "popularity.desc"
) -> List[Dict[str, Any]]:
    """
    Discover movies matching the given genre IDs via TMDB's /discover endpoint.
    """
    genre_str = ",".join(str(i) for i in genre_ids)
    cache_key = f"tmdb_recs_{genre_str}_{limit}_{page}_{sort_by}"
    return await cache_service.get_or_fetch(
        cache_key, _do_fetch_recommendations, ttl=3600, 
        genre_str=genre_str, limit=limit, page=page, sort_by=sort_by
    )


@with_retries()
async def _do_fetch_similar_movies(tmdb_id: int, limit: int) -> List[Dict[str, Any]]:
    api_key = os.getenv("API_KEY")
    async with httpx.AsyncClient(timeout=5.0) as client:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/recommendations?api_key={api_key}"
        response = await client.get(url)
        response.raise_for_status()
        response_data = response.json()
        
        return [
            {
                "tmdb_id": m["id"],
                "title": m.get("title", ""),
                "overview": m.get("overview", ""),
                "vote_average": str(m.get("vote_average", 0)),
                "poster_url": f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get("poster_path") else "",
                "release_date": m.get("release_date", ""),
                "genre_ids": m.get("genre_ids", [])
            }
            for m in response_data.get("results", [])[:limit]
        ]

async def fetch_similar_movies(tmdb_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch movies similar to a specific title using TMDB's /recommendations endpoint.
    """
    cache_key = f"tmdb_similar_{tmdb_id}_{limit}"
    return await cache_service.get_or_fetch(
        cache_key, _do_fetch_similar_movies, ttl=3600, tmdb_id=tmdb_id, limit=limit
    )

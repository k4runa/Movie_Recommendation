import httpx
import os
import asyncio
import random
import logging
from typing import Any, List, Dict
from dotenv import load_dotenv
from services.cache import cache_service
from services.resilience import resilient_call, CircuitBreaker, CircuitBreakerOpen
from functools import wraps

load_dotenv()
logger = logging.getLogger(__name__)

# Fix 6.2: Persistent client for connection pooling
_tmdb_client = None
_tmdb_cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

async def get_tmdb_client() -> httpx.AsyncClient:
    global _tmdb_client
    if _tmdb_client is None or _tmdb_client.is_closed:
        _tmdb_client = httpx.AsyncClient(timeout=10.0, limits=httpx.Limits(max_connections=20))
    return _tmdb_client


# Removed local with_retries implementation in favor of shared resilience utility.


async def fetch_tmdb_data(query: str) -> dict[str, Any]:
    """
    Search TMDB for a movie by title and return the top result's metadata.
    """
    try:
        results = await search_tmdb_movies(query, limit=1)
        return results[0] if results else {}
    except Exception:
        return {}


@resilient_call(retry_on=(httpx.HTTPError, ValueError), circuit_breaker=_tmdb_cb)
async def _do_search_tmdb(query: str, limit: int) -> list[dict[str, Any]]:
    api_key = os.getenv("API_KEY")
    client = await get_tmdb_client()
    try:
        response = await client.get(
            f"https://api.themoviedb.org/3/search/movie?query={query}&api_key={api_key}"
        )
        response.raise_for_status()
        data_response: dict = response.json()
    except Exception as e:
        logger.error(f"TMDB search failed: {e}")
        return []
        
    results = data_response.get("results", []) or []
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
    ] or []

async def search_tmdb_movies(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Search TMDB for movies by title and return a list of results.
    """
    if not query:
        return []
    
    cache_key = f"tmdb_search_{query}_{limit}"
    try:
        return await cache_service.get_or_fetch(cache_key, _do_search_tmdb, ttl=3600, query=query, limit=limit) or []
    except CircuitBreakerOpen:
        return []
    except Exception:
        return []


@resilient_call(retry_on=(httpx.HTTPError, ValueError), circuit_breaker=_tmdb_cb)
async def _do_fetch_tmdb_movie_by_id(tmdb_id: int) -> dict[str, Any]:
    """
    Fetch full metadata for a specific movie by its TMDB ID.
    """
    api_key = os.getenv("API_KEY")
    client = await get_tmdb_client()
    try:
        response = await client.get(
            f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={api_key}"
        )
        response.raise_for_status()
        movie = response.json()
    except Exception as e:
        logger.error(f"TMDB movie fetch failed for {tmdb_id}: {e}")
        return {}
        
    return {
        "tmdb_id": movie["id"],
        "title": movie["title"],
        "overview": movie.get("overview", ""),
        "genre_ids": ",".join(str(g["id"]) for g in movie.get("genres", [])),
        "vote_average": str(movie.get("vote_average", 0)),
        "poster_url": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else "",
        "release_date": movie.get("release_date", ""),
    } or {}

async def fetch_tmdb_movie_by_id(tmdb_id: int) -> dict[str, Any]:
    try:
        return await _do_fetch_tmdb_movie_by_id(tmdb_id) or {}
    except (CircuitBreakerOpen, Exception):
        return {}


@resilient_call(retry_on=(httpx.HTTPError, ValueError), circuit_breaker=_tmdb_cb)
async def _do_fetch_recommendations(genre_str: str, limit: int, page: int, sort_by: str) -> List[Dict[str, Any]]:
    api_key = os.getenv("API_KEY")
    client = await get_tmdb_client()
    try:
        url = f"https://api.themoviedb.org/3/discover/movie?with_genres={genre_str}&api_key={api_key}&page={page}&sort_by={sort_by}"
        response = await client.get(url)
        response.raise_for_status()
        response_data = response.json()
    except Exception as e:
        logger.error(f"TMDB recommendations failed: {e}")
        return []
        
    results = response_data.get("results", []) or []
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
        for m in results[:limit]
    ] or []

async def fetch_recommendations(
    genre_ids: List[int], limit: int = 20, page: int = 1, sort_by: str = "popularity.desc"
) -> List[Dict[str, Any]]:
    """
    Discover movies matching the given genre IDs via TMDB's /discover endpoint.
    """
    genre_str = ",".join(str(i) for i in genre_ids)
    cache_key = f"tmdb_recs_{genre_str}_{limit}_{page}_{sort_by}"
    try:
        return await cache_service.get_or_fetch(
            cache_key, _do_fetch_recommendations, ttl=3600, 
            genre_str=genre_str, limit=limit, page=page, sort_by=sort_by
        ) or []
    except CircuitBreakerOpen:
        return []
    except Exception:
        return []


@resilient_call(retry_on=(httpx.HTTPError, ValueError), circuit_breaker=_tmdb_cb)
async def _do_fetch_similar_movies(tmdb_id: int, limit: int) -> List[Dict[str, Any]]:
    api_key = os.getenv("API_KEY")
    client = await get_tmdb_client()
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/recommendations?api_key={api_key}"
        response = await client.get(url)
        response.raise_for_status()
        response_data = response.json()
    except Exception as e:
        logger.error(f"TMDB similar movies failed: {e}")
        return []
        
    results = response_data.get("results", []) or []
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
        for m in results[:limit]
    ] or []

async def fetch_similar_movies(tmdb_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch movies similar to a specific title using TMDB's /recommendations endpoint.
    """
    cache_key = f"tmdb_similar_{tmdb_id}_{limit}"
    try:
        return await cache_service.get_or_fetch(
            cache_key, _do_fetch_similar_movies, ttl=3600, tmdb_id=tmdb_id, limit=limit
        ) or []
    except CircuitBreakerOpen:
        return []
    except Exception:
        return []

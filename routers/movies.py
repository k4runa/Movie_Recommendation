"""
routers/movies.py — Movie Tracking & Recommendations

Manages the user's movie collection and serves AI-powered
recommendations based on their most-watched genres.

All endpoints require JWT authentication and enforce ownership
checks (a user can only access their own movie data).

Endpoints:
    GET    /movies/{username}/watched              — List tracked movies.
    POST   /movies/{username}                      — Track a new movie.
    DELETE /movies/{username}/{title}               — Remove a tracked movie.
    GET    /movies/recommendations/{username}       — Get personalized recs.
"""

import random
from fastapi import APIRouter, Depends, HTTPException
from services.schemas import MovieScheme, APIResponseWatchedMoviesList
from services.deps import movies_manager, users_manager
from services.auth import get_current_user
from services.tmdb import fetch_recommendations
from services.ai import ai_service

router = APIRouter(prefix="/movies", tags=["movies"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/{username}/watched", response_model=APIResponseWatchedMoviesList)
async def get_watched_movies(
    username: str,
    skip: int = 0,
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
):
    """
    Return a paginated list of movies tracked by the authenticated user.

    Query params:
        skip  — Number of items to skip (default 0).
        limit — Maximum items to return (default 10).
    """
    if current_user.get("username") != username:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resource"
        )
    watched_movies = await movies_manager.get_watched_movies(username, skip=skip, limit=limit)  # type: ignore
    return {"success": True, "data": {"watched_movies": watched_movies}}


@router.delete("/{username}/{movie_id}")
async def delete_movie(
    username: str, movie_id: int, current_user: dict = Depends(get_current_user)
):
    """
    Remove a movie from the authenticated user's tracked collection.

    The `movie_id` path parameter is the database primary key of the
    tracked movie record.  No external API call is required.
    """
    if current_user.get("username") != username:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resource"
        )
    success = await movies_manager.delete_movie(username, movie_id)  # type: ignore
    return {"success": success}


@router.post("/{username}")
async def add_movie(
    username: str, movie: MovieScheme, current_user: dict = Depends(get_current_user)
):
    """
    Search TMDB for a movie and add it to the user's tracked collection.

    The `query` field in the request body is forwarded to TMDB's search
    endpoint; the top result is persisted with full metadata.
    """
    if current_user.get("username") != username:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resource"
        )
    await movies_manager.add_movie(username=username, query=movie.query)  # type: ignore
    return {"success": True, "message": "Movie successfully added."}


@router.get("/recommendations/{username}")
async def get_recommendations(
    username: str, current_user: dict = Depends(get_current_user)
):
    """
    Generate personalized movie recommendations for the authenticated user.

    Algorithm:
        1. Analyse the user's tracked movies to find their top 5 genres.
        2. Query TMDB's /discover endpoint with those genre IDs (up to 20 results).
        3. Filter out any movies the user has already tracked.
        4. Shuffle the remaining results for variety and return the top 10.

    Returns an empty list (not an error) if the user hasn't tracked enough
    movies to generate meaningful recommendations.
    """
    if current_user.get("username") != username:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resource"
        )

    # Fetch all tracked movies to build a set of IDs to exclude
    watched = await movies_manager.get_watched_movies(username, skip=0, limit=1000)  # type: ignore
    watched_tmdb_ids = {m.get("tmdb_id") for m in watched}

    # Discover similar movies based on the user's top genres
    top_genres = await movies_manager.get_top_genres(username)
    recommendations = await fetch_recommendations(top_genres, limit=20)

    # Remove already-tracked movies from the result set
    filtered_recs = [
        r for r in recommendations if r.get("tmdb_id") not in watched_tmdb_ids
    ]

    # Shuffle for variety — prevents the same order on every page load
    random.shuffle(filtered_recs)
    final_recs = filtered_recs[:10]

    # Optionally enrich with AI-generated explanations if Gemini is active and user enabled AI
    user_db = await users_manager.get_user_by_username(username)
    if ai_service.active and watched and user_db.get("ai_enabled"):
        watched_titles = [m.get("title") for m in watched[-10:]]  # Use last 10 for context
        explanations = await ai_service.explain_recommendations(watched_titles, final_recs)
        for r in final_recs:
            r["ai_reason"] = explanations.get(r.get("title","N/A"),"N/A")

    return {"success": True, "data": {"recommendations": final_recs}}


@router.get("/ai-insights/{username}")
async def get_ai_insights(username: str, current_user: dict = Depends(get_current_user)):
    """
    Generate a personalized movie taste profile using Gemini AI.
    Analyzes the user's watch history (titles + overviews) to describe
    their cinematic personality.
    """
    if current_user.get("username") != username:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resource"
        )

    if not ai_service.active:
        return {"success": False, "message": "AI service is not configured."}

    user_db = await users_manager.get_user_by_username(username)
    if not user_db.get("ai_enabled"):
        return {"success": False, "message": "AI features are disabled by the user."}

    # Fetch last 20 movies for analysis context
    watched = await movies_manager.get_watched_movies(username, skip=0, limit=20)  # type: ignore
    if not watched:
        return {
            "success": True,
            "data": {"insight": "Start tracking some movies to get AI insights!"},
        }

    insight = await ai_service.analyze_user_taste(watched)
    return {"success": True, "data": {"insight": insight}}

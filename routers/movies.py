import random
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from services.deps import movies_manager, users_manager, limiter
from services.tmdb import (
    fetch_recommendations,
    fetch_similar_movies,
)
from services.auth import get_current_user
from services.schemas import MovieScheme
from services.ai import ai_service
from services.discovery.manager import DiscoveryManager
from services.tmdb import fetch_tmdb_movie_by_id
import asyncio
from services.database import logger
from services.cache import cache_service

discovery_manager = DiscoveryManager()
router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get("/all/trending")
@router.get("/all/trending/")
@limiter.limit("20/minute")
async def get_trending_movies(request: Request, limit: int = 20, current_user: dict = Depends(get_current_user)):
    """
    Fetch trending movies from TMDB for the dashboard.
    """
    username = current_user["username"]
    # Get all TMDB IDs the user has already tracked/added
    tracked_ids = await movies_manager.get_all_tracked_tmdb_ids(username) # type: ignore
    
    # Fetch slightly more to account for filtered items
    fetch_limit = limit + len(tracked_ids)
    results = await fetch_recommendations(genre_ids=[], limit=fetch_limit, sort_by="popularity.desc")
    
    # Filter out movies that are already tracked (including favorites)
    filtered_results = [m for m in results if m.get("tmdb_id") not in tracked_ids]
    
    return {"success": True, "data": {"results": filtered_results[:limit]}}


@router.get("/discovery/{entity_id}")
async def get_discovery_details(entity_id: str, skip_ai: bool = False, current_user: dict = Depends(get_current_user)):
    """Fetch details for a discovery entity by its canonical ID."""
    dm = DiscoveryManager()
    entity = await dm.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found or cache expired.")
    
    # Add AI Perspective
    movie_dict = entity.model_dump()
    username = current_user["username"]

    # Check cache first to avoid re-generating for the same user/entity
    cache_key = f"ai_reason_{username}_{entity_id}"
    cached_ai = await cache_service.get(cache_key)
    if cached_ai:
        movie_dict["ai_reason"] = cached_ai
        return {"success": True, "data": movie_dict}

    watched = await movies_manager.get_watched_movies(username, limit=5) # type: ignore
    
    ai_reason = "A highly regarded film worth checking out."
    if ai_service.active and watched and not skip_ai:
        try:
            watched_titles = [m.get("title") for m in watched]
            reasons = await asyncio.wait_for(
                ai_service.explain_recommendations(watched_titles, [movie_dict]),
                timeout=12.0
            )
            ai_reason = reasons.get(movie_dict["title"], ai_reason)
            # Cache the successful AI generation for 1 hour
            await cache_service.set(cache_key, ai_reason, ttl=3600)
        except asyncio.TimeoutError:
            ai_reason = "Eco's overview is taking a bit longer than usual. The movie should be great though!"
        except Exception as e:
            logger.error(f"Discovery AI generation failed: {e}")
            
    movie_dict["ai_reason"] = ai_reason
    return {"success": True, "data": movie_dict}


@router.get("/details/{tmdb_id}")
async def get_movie_details(tmdb_id: int, skip_ai: bool = False, passed_ai_reason: str = None, current_user: dict = Depends(get_current_user)):
    """
    Fetch full movie details along with an AI-generated explanation of why the user might like it.
    """

    movie = await fetch_tmdb_movie_by_id(tmdb_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
        
    username = current_user["username"]
    
    # Check cache first
    cache_key = f"ai_reason_{username}_tmdb_{tmdb_id}"
    from services.cache import cache_service
    cached_ai = await cache_service.get(cache_key)
    if cached_ai:
        movie["ai_reason"] = cached_ai
        return {"success": True, "data": movie}

    watched = await movies_manager.get_watched_movies(username, limit=5) # type: ignore
    
    ai_reason = "A highly regarded film worth checking out."
    if ai_service.active and watched and not skip_ai:
        try:
            watched_titles = [m.get("title") for m in watched]
            reasons = await asyncio.wait_for(
                ai_service.explain_recommendations(watched_titles, [movie]),
                timeout=12.0
            )
            ai_reason = reasons.get(movie["title"], ai_reason)
            # Cache for 1 hour
            await cache_service.set(cache_key, ai_reason, ttl=3600)
        except asyncio.TimeoutError:
            # Graceful degradation
            ai_reason = "AI analysis is currently taking too long. Enjoy the movie!"
        except Exception as e:
            logger.error(f"AI detail generation failed: {e}")
        
    movie["ai_reason"] = ai_reason
    return {"success": True, "data": movie}



@router.get("/search")
@limiter.limit("20/minute")
async def search_movies(
    request: Request,
    query: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    """
    Search for movies across multiple providers (TMDB, AniList, etc.).
    Authentication required — prevents anonymous abuse of the proxy.
    """
    results = await discovery_manager.search_all(query, limit=limit)
    return {"success": True, "data": {"results": results}}


@router.get("/filter-by-release-date")
@router.get("/filter-by-release-date/")
@limiter.limit("20/minute")
async def get_movies_filter_by_release_date(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Return a paginated list of movies tracked by the authenticated user.
    """
    username = current_user["username"]
    movies = await movies_manager.filter_by_release_date(username)  # type: ignore
    return {"success": True, "data": {"movies": movies}}


@router.get("/filter-by-added-date")
@router.get("/filter-by-added-date/")
@limiter.limit("20/minute")
async def get_movies_filter_by_added_date(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Return a paginated list of movies tracked by the authenticated user.
    """
    username = current_user["username"]
    movies = await movies_manager.filter_by_added_date(username)  # type: ignore
    return {"success": True, "data": {"movies": movies}}



@router.get("/filter-by-rating/{rating}")
@router.get("/filter-by-rating/{rating}/")
@limiter.limit("20/minute")
async def get_movies_filter_by_rating(request: Request, rating: int, current_user: dict = Depends(get_current_user)):
    """
    Return a paginated list of movies tracked by the authenticated user.
    """
    username = current_user["username"]
    movies = await movies_manager.filter_by_rating(username, rating)  # type: ignore
    return {"success": True, "data": {"movies": movies}}


@router.get("/")
async def get_movies(skip: int = 0, limit: int = 20, current_user: dict = Depends(get_current_user)):
    """
    Return a paginated list of movies tracked by the authenticated user.
    """
    username = current_user["username"]
    watched_movies = await movies_manager.get_watched_movies(username, skip=skip, limit=limit)  # type: ignore
    return {"success": True, "data": {"watched_movies": watched_movies}}


@router.delete("/{movie_id}")
async def delete_movie(movie_id: int, current_user: dict = Depends(get_current_user)):
    """
    Remove a movie from the authenticated user's tracked collection.
    """
    username = current_user["username"]
    success = await movies_manager.delete_movie(username, movie_id) #type: ignore
    return {"success": success}


@router.post("/")
async def add_movie(movie: MovieScheme, current_user: dict = Depends(get_current_user)):
    """
    Add a movie to the user's collection.
    """
    username = current_user["username"]
    await movies_manager.add_movie(username=username, movie_data=movie)  # type: ignore
    return {"success": True, "message": "Movie successfully added."}


@router.post("/{movie_id}/favorite")
async def toggle_favorite(movie_id: int, current_user: dict = Depends(get_current_user)):
    """
    Toggle the favorite status of a movie. Max 3 favorites per user.
    """
    username = current_user["username"]
    try:
        result = await movies_manager.toggle_favorite(username=username, movie_id=movie_id) # type: ignore
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/favorites")
async def get_favorites(current_user: dict = Depends(get_current_user)):
    """
    Fetch the authenticated user's favorite movies.
    """
    username = current_user["username"]
    favorites = await movies_manager.get_favorites(username) # type: ignore
    return {"success": True, "data": {"favorites": favorites}}

@router.get("/recommendations")
async def get_recommendations(current_user: dict = Depends(get_current_user)):
    """
    Generate highly personalized movie recommendations.

    Logic:
    1. Title-Based: Pick 2-3 random movies from user's library and find similar titles.
    2. Genre-Based: Find top genres and discover movies in those genres (for variety).
    3. Merge, filter watched, and shuffle.
    """
    username = current_user["username"]
    # 1. Get user's current library
    watched             =   await movies_manager.get_watched_movies(username, limit=100)    #type: ignore
    watched_tmdb_ids    =   await movies_manager.get_all_tracked_tmdb_ids(username)         #type: ignore
    all_candidates = []
    # 2. Strategy A: Specific Similarity (Title-based)
    if watched:
        sample_size     =   min(len(watched), 3)
        sample_movies   =   random.sample(watched, sample_size)
        for movie in sample_movies:
            tmdb_id     =   movie.get("tmdb_id")
            if tmdb_id:
                similar = await fetch_similar_movies(tmdb_id, limit=15)
                all_candidates.extend(similar)
    # 3. Strategy B: Broad Discovery (Genre-based)
    top_genres          =   await movies_manager.get_top_genres(username)
    if top_genres:
        num_genres      =   min(len(top_genres), random.randint(2, 3))
        selected_genres =   random.sample(top_genres, num_genres)
        sort_options    =   ["popularity.desc", "vote_average.desc", "revenue.desc"]
        random_sort     =   random.choice(sort_options)
        random_page     =   random.randint(1, 10)

        genre_recs      =   await fetch_recommendations(selected_genres, limit=20, page=random_page, sort_by=random_sort)
        all_candidates.extend(genre_recs)
    # 4. Deduplicate and Filter
    seen_ids            =   set()
    unique_candidates   =   []
    for m in all_candidates:
        tid             =   m.get("tmdb_id")
        if tid and tid not in watched_tmdb_ids and tid not in seen_ids:
            unique_candidates.append(m)
            seen_ids.add(tid)
    # 5. Fallback: If still empty, just get some popular movies
    if not unique_candidates:
        fallback_genre      =   ([top_genres[0]] if top_genres else [28])  # Default to action if no genres
        unique_candidates   =   await fetch_recommendations(fallback_genre, limit=20, page=1)
    # 6. Final Polish
    unique_candidates       = unique_candidates if unique_candidates else []
    random.shuffle(unique_candidates)
    final_recs              =   unique_candidates[:12]
    # 7. Add AI Reasons
    user_db                 =   await users_manager.get_user_by_username(username)  #type: ignore
    if ai_service.active and user_db.get("ai_enabled"):
        try:
            watched_titles = [m.get("title") for m in watched[-10:]]
            # Timeout after 12 seconds for bulk recommendations
            raw_explanations = await asyncio.wait_for(
                ai_service.explain_recommendations(watched_titles, final_recs),
                timeout=12.0
            )

            explanations = ai_service._parse_explanations(raw_explanations) if isinstance(raw_explanations, str) else raw_explanations
            
            for r in final_recs:
                reason = explanations.get(r.get("title","N/A"))
                if not reason or reason.upper() == "N/A":
                    r["ai_reason"] = "A handpicked selection matching your unique cinematic preferences."
                else:
                    r["ai_reason"] = reason
        except Exception as e:
            logger.error(f"Bulk AI recommendation failed: {e}")
            for r in final_recs:
                r["ai_reason"] = "I've picked this one because it's a timeless gem that matches your vibe! <3"

    return {"success": True, "data": {"recommendations": final_recs}}

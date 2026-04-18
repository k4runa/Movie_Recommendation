import random
from fastapi import APIRouter, Depends, HTTPException
from services.deps import movies_manager, users_manager
from services.tmdb import (
    search_tmdb_movies,
    fetch_recommendations,
    fetch_similar_movies,
)
from services.auth import get_current_user
from services.schemas import MovieScheme
from services.ai import ai_service

router              =   APIRouter(prefix="/movies", tags=["Movies"])


@router.get("/search")
async def search_movies(query: str, limit: int = 10):
    """
    Search for movies on TMDB and return a list of results.
    """
    results         =   await search_tmdb_movies(query, limit=limit)
    return {"success": True, "data": {"results": results}}


@router.get("/{username}")
async def get_movies(username: str,skip: int = 0,limit: int = 20,current_user: dict = Depends(get_current_user),):
    """
    Return a paginated list of movies tracked by the authenticated user.
    """
    if current_user.get("username") != username:
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    watched_movies  =   await movies_manager.get_watched_movies(username, skip=skip, limit=limit)  # type: ignore
    return {"success": True, "data": {"watched_movies": watched_movies}}


@router.delete("/{username}/{movie_id}")
async def delete_movie(username: str, movie_id: int, current_user: dict = Depends(get_current_user)):
    """
    Remove a movie from the authenticated user's tracked collection.
    """
    if current_user.get("username") != username:
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    success         =   await movies_manager.delete_movie(username, movie_id) #type: ignore
    return {"success": success}


@router.post("/{username}")
async def add_movie(username: str, movie: MovieScheme, current_user: dict = Depends(get_current_user)):
    """
    Add a movie to the user's collection.
    """
    if current_user.get("username") != username:
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    await movies_manager.add_movie(username=username, query=movie.query, tmdb_id=movie.tmdb_id)  # type: ignore
    return {"success": True, "message": "Movie successfully added."}


@router.get("/recommendations/{username}")
async def get_recommendations(username: str, current_user: dict = Depends(get_current_user)):
    """
    Generate highly personalized movie recommendations.

    Logic:
    1. Title-Based: Pick 2-3 random movies from user's library and find similar titles.
    2. Genre-Based: Find top genres and discover movies in those genres (for variety).
    3. Merge, filter watched, and shuffle.
    """
    if current_user.get("username") != username:
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    # 1. Get user's current library
    watched             =   await movies_manager.get_watched_movies(username, limit=100)    #type: ignore
    watched_tmdb_ids    =   await movies_manager.get_all_tracked_tmdb_ids(username)         #type: ignore

    all_candidates = []

    # 2. Strategy A: Specific Similarity (Title-based)
    if watched:
        # Pick up to 3 random movies to base recommendations on
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
        # Pick a random subset of 2-3 genres
        num_genres      =   min(len(top_genres), random.randint(2, 3))
        selected_genres =   random.sample(top_genres, num_genres)
        # Pick random sort and page
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
        # Last resort: just some popular movies in their top genre
        fallback_genre      =   ([top_genres[0]] if top_genres else [28])  # Default to action if no genres
        unique_candidates   =   await fetch_recommendations(fallback_genre, limit=20, page=1)

    # 6. Final Polish
    random.shuffle(unique_candidates)
    final_recs              =   unique_candidates[:12]

    # 7. Add AI Reasons
    user_db                 =   await users_manager.get_user_by_username(username)  #type: ignore
    if ai_service.active and watched and user_db.get("ai_enabled"):
        watched_titles      =   [m.get("title") for m in watched[-10:]]
        explanations        =   await ai_service.explain_recommendations(watched_titles, final_recs)
        for r in final_recs:
            reason = explanations.get(r.get("title","N/A"))
            if not reason or reason.upper() == "N/A":
                r["ai_reason"] = ("A handpicked selection matching your unique cinematic preferences.")
            else:
                r["ai_reason"] = reason

    return {"success": True, "data": {"recommendations": final_recs}}

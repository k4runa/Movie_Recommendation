from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from services.ai import ai_service
from services.auth import get_current_user
from services.database import logger
from fastapi.responses import StreamingResponse
from services.deps import movies_manager, limiter

router = APIRouter(prefix="/ai", tags=["AI"])


class ChatMessage(BaseModel):
    role:       str = Field(..., max_length=20)
    content:    str = Field(..., max_length=5000)


class ChatRequest(BaseModel):
    message:        str                         = Field(..., min_length=1, max_length=5000)
    history:        list[ChatMessage] | None     = Field(None, max_length=20)
    stream:         bool                        = Field(False)


@router.post("/chat")
@limiter.limit("10/minute")
async def chat_with_ai(request: Request, payload: ChatRequest, current_user: dict = Depends(get_current_user)):
    """
    General AI Chat endpoint with optional Streaming.
    """
    if not ai_service.active:
        raise HTTPException(status_code=503, detail="AI service is currently unavailable.")
    try:
        # Fetch user's movies to provide context
        import random
        username                =   current_user.get("username")
        all_user_movies         =   await movies_manager.get_watched_movies(username, limit=50) #type: ignore
        user_movies             =   random.sample(all_user_movies, min(len(all_user_movies), 20)) if all_user_movies else []
        
        # 1. Build sanitized movie list — prevents injection via crafted movie titles
        raw_titles              =   [m.get("title", "Unknown") for m in user_movies]
        movie_list              =   ", ".join(ai_service._sanitize_context(t) for t in raw_titles)

        # 2. Get AI taste summary (Memory enhancement)
        raw_taste               =   await ai_service.analyze_user_taste(user_movies) or "No specific taste profile yet."
        taste_summary           =   ai_service._sanitize_context(raw_taste)
        
        # Build system context
        system_context          =   "YOU ARE ECO, a professional and knowledgeable cinematic expert. Provide insightful movie guidance.\n\n"
        system_context          +=  "--- BACKGROUND DATA (Use SUBTLY only if relevant and NOT already discussed) ---\n"
        system_context          +=  f"Username: {username}\n"
        system_context          +=  f"User's Viewing Preferences: {taste_summary}\n"
        system_context          +=  f"Library Content: {movie_list}\n\n"
        
        system_context          +=  "--- CONVERSATIONAL RULES ---\n"
        system_context          +=  "1. PERSISTENCE: Check the chat history. If you've already mentioned something from the 'Background Data', DO NOT repeat it.\n"
        system_context          +=  "2. DIVERSITY: If the user asks for 'something else', stay AWAY from their usual taste.\n"
        system_context          +=  "3. BREVITY: Keep it conversational. No 'As an AI' phrases.\n"
        system_context          +=  "4. TONE: Maintain a professional and helpful personality. Avoid emojis or informal symbols.\n"
        system_context          +=  "5. FORMATTING: Use **Bold** for movie titles.\n"

        # Build context from history — sanitize each message to prevent injection via history
        history_context         =   ""
        if payload.history:
            history_lines       =   [f"{msg.role}: {ai_service._sanitize_context(msg.content)}" for msg in payload.history]
            history_context     =   "\n".join(history_lines)

        full_context            =   system_context + "\n" + history_context

        if payload.stream:
            async def event_generator():
                full_response = ""
                async for chunk in ai_service.stream_chat(payload.message, context=full_context):
                    full_response += chunk
                    yield chunk
                # Persistence: Save to DB after stream completes
                try:
                    from services.deps import ai_manager
                    await ai_manager.add_message(username=username, role="user", content=payload.message)
                    await ai_manager.add_message(username=username, role="assistant", content=full_response)
                except Exception as pe:
                    logger.error(f"Failed to persist streamed AI message: {pe}")

            return StreamingResponse(event_generator(), media_type="text/event-stream")

        # Non-streaming JSON response
        response_text           =   await ai_service.chat(payload.message, context=full_context)

        # Persistence: Save both messages to database
        try:
            from services.deps import ai_manager
            await ai_manager.add_message(username=username, role="user", content=payload.message)
            await ai_manager.add_message(username=username, role="assistant", content=response_text)
        except Exception as pe:
            logger.error(f"Failed to persist AI message: {pe}")

        return {"success": True, "response": response_text}

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred while processing your request.")


@router.get("/history")
async def get_chat_history(current_user: dict = Depends(get_current_user)):
    """
    Fetch persistent chat history for the current user.
    """
    from services.deps import ai_manager
    username = current_user.get("username")
    messages = await ai_manager.get_history(username=username)
    return {"success": True, "data": messages}


@router.delete("/history")
async def clear_chat_history(current_user: dict = Depends(get_current_user)):
    """
    Clear all chat history for the current user.
    """
    from services.deps import ai_manager
    username = current_user.get("username")
    await ai_manager.clear_history(username=username)
    return {"success": True, "message": "History cleared."}
@router.get("/recommendations")
@limiter.limit("10/minute")
async def get_ai_recommendations(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Eco-powered recommendations based on user history.
    """
    if not ai_service.active:
        return {"success": False, "detail": "AI service inactive"}
    
    import random
    username = current_user.get("username")
    all_user_movies = await movies_manager.get_watched_movies(username, limit=100) #type: ignore
    
    # Kütüphaneden rastgele 20 film seçerek her seferinde farklı ve homojen bir bağlam sunuyoruz
    user_movies = random.sample(all_user_movies, min(len(all_user_movies), 20)) if all_user_movies else []
    
    if not user_movies:
        return {"success": True, "data": []}
    
    # Get titles from AI
    suggested_titles = await ai_service.generate_ai_recommendations(user_movies)
    
    # Resolve to TMDB movies in parallel
    from services.tmdb import search_tmdb_movies
    import asyncio
    
    async def resolve_title(title):
        try:
            search_res = await search_tmdb_movies(title)
            if search_res:
                m = search_res[0]
                if m.get("tmdb_id"):
                    return {
                        "id": m.get("tmdb_id"),
                        "tmdb_id": m.get("tmdb_id"),
                        "title": m.get("title"),
                        "poster_url": m.get("poster_url") or None,
                        "vote_average": m.get("vote_average"),
                        "release_date": m.get("release_date")
                    }
        except Exception:
            pass
        return None

    # Limit to 10 titles to avoid overwhelming TMDB API
    tasks = [resolve_title(t) for t in suggested_titles[:10]]
    resolved_results = await asyncio.gather(*tasks)
    resolved_movies = [m for m in resolved_results if m is not None]
            
    return {"success": True, "data": resolved_movies}

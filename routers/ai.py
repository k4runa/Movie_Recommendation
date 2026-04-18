from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.ai import ai_service
from services.auth import get_current_user
from services.database import logger
from fastapi.responses import StreamingResponse
from services.deps import movies_manager

router = APIRouter(prefix="/ai", tags=["AI"])

class ChatRequest(BaseModel):
    message:        str
    history:        list[dict[str, str]] | None = None

@router.post("/chat")
async def chat_with_ai(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """
    General AI Chat endpoint with Streaming.
    """
    if not ai_service.active:
        raise HTTPException(status_code=503, detail="AI service is currently unavailable.")

    try:
        # Fetch user's movies to provide context
        username                =   current_user.get("username")
        user_movies             =   await movies_manager.get_watched_movies(username, limit=50) #type: ignore
        
        # 1. Get raw movie list
        movie_list              =   ", ".join([m.get("title", "Unknown") for m in user_movies])

        # 2. Get AI taste summary (Memory enhancement)
        # This gives Eco a deeper understanding of "who" the user is
        taste_summary           =   await ai_service.analyze_user_taste(user_movies) or "No specific taste profile yet."

        # Build system context
        system_context          =   f"User: {username}\n"
        system_context          =   system_context + f"User's Cinematic Profile: {taste_summary}\n"
        system_context          =  system_context + f"Recent Tracked Movies: {movie_list}\n"
        system_context          =  system_context + "You are Eco, the CineWave AI Assistant. Your name is Eco. You know the user's movie taste based on their tracked list and profile. Provide personalized recommendations and answer questions with this context in mind. Be concise and professional. Respond ONLY in English. Use Markdown for formatting (e.g., **bold** for movie titles, lists for multiple recommendations).\n"

        # Build context from history if provided
        history_context         =   ""
        if request.history:
            history_lines       =   [f"{msg.get('role', 'user')}: {msg.get('content', '')}"for msg in request.history]
            history_context     =   "\n".join(history_lines)

        full_context            =   system_context + "\n" + history_context

        async def event_generator():
            async for chunk in ai_service.stream_chat(request.message, context=full_context):
                yield chunk

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

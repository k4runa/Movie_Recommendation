from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.ai import ai_service
from services.auth import get_current_user
from services.database import logger

router = APIRouter(prefix="/ai", tags=["AI"])

from typing import List, Dict, Optional, Any


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None


from services.deps import movies_manager


@router.post("/chat")
async def chat_with_ai(
    request: ChatRequest, current_user: dict = Depends(get_current_user)
):
    """
    General AI Chat endpoint.
    Uses the multi-provider service with rotation and fallback.
    """
    if not ai_service.active:
        raise HTTPException(
            status_code=503, detail="AI service is currently unavailable."
        )

    try:
        # Fetch user's movies to provide context
        username = current_user.get("username")
        user_movies = await movies_manager.get_watched_movies(username, limit=50)

        movie_list = ", ".join([m.get("title", "Unknown") for m in user_movies])

        # Build system context
        system_context = f"User: {username}\n"
        system_context += f"User's Tracked Movies: {movie_list}\n"
        system_context += "You are Eco, the CineWave AI Assistant. Your name is Eco. You know the user's movie taste based on their tracked list. Provide personalized recommendations and answer questions with this context in mind. Be concise and professional. Respond ONLY in English.\n"

        # Build context from history if provided
        history_context = ""
        if request.history:
            history_lines = [
                f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in request.history
            ]
            history_context = "\n".join(history_lines)

        full_context = system_context + "\n" + history_context

        response = await ai_service.chat(request.message, context=full_context)
        return {"response": response}
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

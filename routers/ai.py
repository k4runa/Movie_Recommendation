from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.ai import ai_service
from services.auth import get_current_user
from services.database import logger

router = APIRouter(prefix="/ai", tags=["AI"])

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat_with_ai(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """
    General AI Chat endpoint. 
    Uses the multi-provider service with rotation and fallback.
    """
    if not ai_service.active:
        raise HTTPException(status_code=503, detail="AI service is currently unavailable.")
    
    try:
        # We can pass user context here if needed
        response = await ai_service.chat(request.message)
        return {"response": response}
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

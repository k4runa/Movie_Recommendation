"""
routers/social.py — Social Networking Endpoints

Handles messaging, similar minds discovery, and privacy settings.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from services.deps import social_manager, limiter
from services.auth import get_current_user
from services.schemas import (
    MessageCreate,
    MessageUpdate,
    PrivacyUpdate,
)
import asyncio

router = APIRouter(prefix="/social", tags=["social"])

@router.get("/similar", response_model=dict)
@limiter.limit("120/minute")
async def get_similar_minds(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Retrieve a list of users with similar movie tastes.
    Returns pre-calculated similarity scores and reasons.
    """
    user_id = current_user["id"]
    # Recalculate similarities in the background (Fixed 4.5)
    asyncio.create_task(social_manager.recalculate_user_similarity(user_id))

    matches = await social_manager.get_similar_users(user_id)   #type: ignore
    return {"success": True, "data": {"matches": matches}}


@router.post("/message", response_model=dict)
@limiter.limit("30/minute")
async def send_private_message(request: Request,msg_data: MessageCreate,current_user: dict = Depends(get_current_user)):
    """
    Send a private message to another user.
    """
    sender_id = current_user["id"]

    try:
        msg = await social_manager.send_message(sender_id, msg_data.receiver_id, msg_data.content) #type: ignore
        return {"success": True, "data": {"message_id": msg.id}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/message/{message_id}", response_model=dict)
@limiter.limit("30/minute")
async def edit_message(request: Request,message_id: int,msg_data: MessageUpdate,current_user: dict = Depends(get_current_user)):
    """
    Edit a previously sent message.
    """
    user_id = current_user["id"]

    try:
        msg = await social_manager.edit_message(message_id, user_id, msg_data.content) #type: ignore
        return {
            "success": True, 
            "data": {
                "message": {
                    "id": msg.id,
                    "content": msg.content,
                    "is_edited": msg.is_edited,
                    "edited_at": msg.edited_at,
                    "created_at": msg.created_at
                }
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/message/{message_id}", response_model=dict)
@limiter.limit("30/minute")
async def delete_message(request: Request,message_id: int,current_user: dict = Depends(get_current_user)):
    """
    Permanently delete a message (only if you are the sender).
    """
    user_id = current_user["id"]

    await social_manager.delete_message(message_id, user_id)    #type: ignore
    return {"success": True}


@router.get("/conversations", response_model=dict)
@limiter.limit("100/minute")
async def get_conversations(request: Request,status: str = "ACCEPTED", skip: int = 0, limit: int = 50, current_user: dict = Depends(get_current_user)):
    """
    Fetch all conversations for the current user.
    status: 'ACCEPTED' for normal inbox, 'PENDING' for message requests.
    """
    user_id = current_user["id"]
        
    conversations = await social_manager.get_conversations(user_id, status=status, skip=skip, limit=limit)  #type: ignore
    return {"success": True, "data": {"conversations": conversations}}


@router.patch("/requests/{other_user_id}/{action}", response_model=dict)
@limiter.limit("10/minute")
async def handle_message_request(request: Request,other_user_id: int,action: str,current_user: dict = Depends(get_current_user)):
    """
    Accept or Decline a message request from another user.
    action: 'accept' or 'decline'
    """
    if action not in ["accept", "decline"]:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'accept' or 'decline'.")

    user_id = current_user["id"]

    try:
        await social_manager.handle_request(user_id, other_user_id, action) #type: ignore
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/messages/{other_user_id}", response_model=dict)
@limiter.limit("100/minute")
async def get_message_history(request: Request,other_user_id: int, skip: int = 0, limit: int = 50, current_user: dict = Depends(get_current_user)):
    """
    Fetch full message history with another user.
    """
    user_id = current_user["id"]
        
    messages = await social_manager.get_messages(user_id, other_user_id, skip=skip, limit=limit)    #type: ignore
    return {"success": True, "data": {"messages": messages}}


@router.patch("/messages/{other_user_id}/read", response_model=dict)
@limiter.limit("30/minute")
async def mark_messages_read(request: Request,other_user_id: int,current_user: dict = Depends(get_current_user)):
    """
    Mark all messages from another user as read.
    """
    user_id = current_user["id"]
        
    await social_manager.mark_messages_as_read(user_id, other_user_id) #type: ignore
    return {"success": True}


@router.delete("/conversation/{other_user_id}", response_model=dict)
@limiter.limit("5/minute")
async def delete_conversation(request: Request,other_user_id: int,current_user: dict = Depends(get_current_user)):
    """
    Delete the conversation history with another user for the current user.
    """
    user_id = current_user["id"]
        
    await social_manager.delete_conversation(user_id, other_user_id)    #type: ignore
    return {"success": True}


@router.patch("/privacy", response_model=dict)
@limiter.limit("20/minute")
async def update_privacy_settings(request: Request,privacy: PrivacyUpdate,current_user: dict = Depends(get_current_user)):
    """
    Enable or disable public profile discovery in 'Similar Minds'.
    """
    user_id = current_user["id"]

    success = await social_manager.update_privacy(user_id, privacy.is_private)  #type: ignore
    return {"success": success}

@router.get("/profile/{user_id}", response_model=dict)
@limiter.limit("10/minute")
async def get_user_profile(request: Request,user_id: int,current_user: dict = Depends(get_current_user)):
    """
    Fetch public profile data for a user (favorites, top genres, basic info).
    """
    try:
        profile = await social_manager.get_profile(user_id) #type: ignore
        return {"success": True, "data": profile}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

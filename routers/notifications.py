"""
routers/notifications.py — Notification Endpoints

Handles fetching and managing user notifications.
"""

from fastapi import APIRouter, Depends, Request
from services.deps import notification_manager, limiter
from services.auth import get_current_user
from typing import Optional

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/", response_model=dict)
@limiter.limit("60/minute")
async def get_notifications(request: Request, limit: int = 50, current_user: dict = Depends(get_current_user)):
    """
    Fetch all notifications for the current user.
    """
    limit = min(limit, 100)  # Hard cap to prevent unbounded queries
    user_id = current_user["id"]
    notifications = await notification_manager.get_notifications(user_id, limit=limit) #type: ignore
    
    return {
        "success": True,
        "data": notifications
    }

@router.get("/unread/count", response_model=dict)
@limiter.limit("60/minute")
async def get_unread_count(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Get the count of unread notifications.
    """
    user_id = current_user["id"]
    count = await notification_manager.get_unread_count(user_id) #type: ignore
    
    return {
        "success": True,
        "data": {"count": count}
    }

@router.patch("/read", response_model=dict)
@limiter.limit("20/minute")
async def mark_notifications_read(request: Request, notification_id: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    """
    Mark one or all notifications as read.
    """
    user_id = current_user["id"]
    await notification_manager.mark_as_read(user_id, notification_id) #type: ignore
    
    return {"success": True}

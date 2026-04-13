from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.database import logger
from services.deps import users_manager
from services.schemas import UserScheme, APIResponseUser, APIResponseUsersList
from services.auth import get_current_user
from functools import wraps

router = APIRouter(prefix="/users", tags=["users"])

class UpdateUserRequest(BaseModel):
    field: str
    value: str

def print_log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"running function: {func.__name__}")
        result = func(*args, **kwargs)
        logger.info(f"done function: {func.__name__}")
        return result
    return wrapper

@router.post("")
@print_log
def register(user: UserScheme):
    users_manager.add_user(user)  # type:ignore
    return {"success": True, "message": "User successfully added."}

@router.get("", response_model=APIResponseUsersList)
@print_log
def get_all_users(skip: int = 0, limit: int = 10, current_user: dict = Depends(get_current_user)):
    user_in_db = users_manager.get_user_by_username(current_user["username"]) # type: ignore
    if user_in_db.get("role") != "admin":
         raise HTTPException(status_code=403, detail="Admin privileges required")
         
    logger.info(f"Fetching users with skip={skip}, limit={limit}...")
    all_users = users_manager.get_all_users(skip=skip, limit=limit)  # type: ignore
    return {"success": True, "data": {"users": all_users}}

@router.get("/id/{id}", response_model=APIResponseUser)
@print_log
def get_user_by_id(id: int):
    user = users_manager.get_user_by_id(id)  # type: ignore
    return {"success": True, "data": {"user": user}}

@router.get("/{username}", response_model=APIResponseUser)
@print_log
def get_user_by_username(username: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("username") != username:
         raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    user = users_manager.get_user_by_username(username)  # type: ignore
    return {"success": True, "data": {"user": user}}

@router.delete("/{username}")
@print_log
def delete_user(username: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("username") != username:
         raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    success = users_manager.delete_user(username)  # type: ignore
    return {"success": success}

@router.patch("/{username}")
@print_log
def update_user_field(username: str, v: UpdateUserRequest, current_user: dict = Depends(get_current_user)):
    if current_user.get("username") != username:
         raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    success = users_manager.update_user_field(username, v.field, v.value)  # type: ignore
    return {"success": success}

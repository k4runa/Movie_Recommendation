from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from services.auth import verify_password, create_access_token
from services.database import UserNotFoundError
from services.deps import users_manager

router = APIRouter(tags=["auth"])

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user_in_db = users_manager.get_user_by_username(form_data.username) # type: ignore
    except UserNotFoundError:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    if not verify_password(form_data.password, user_in_db.get("password", "")):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
        
    access_token = create_access_token(data={"sub": user_in_db["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

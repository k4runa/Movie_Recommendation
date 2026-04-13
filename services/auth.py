import os
import bcrypt
import logging
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

# FastAPI will expect the token to be sent in the "Authorization" header as "Bearer <token>"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # Check carefully since bcrypt.checkpw requires bytes
        if isinstance(plain_password, str):
            plain_password = plain_password.encode("utf-8")
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode("utf-8")
            
        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error checking password: {e}")
        return False

def create_access_token(data: dict):
    if not SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY not found in environment variables.")
        
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# This is a dependency we'll inject into our protected routes
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not SECRET_KEY:
        logger.error("SECRET_KEY missing when trying to validate token.")
        raise credentials_exception
        
    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
        # We can extract any other info we injected in the token (like id)
        token_data = {"username": username}
        return token_data
        
    except jwt.ExpiredSignatureError:
        logger.warning(f"Token expired for user validation.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise credentials_exception

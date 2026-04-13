from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional

class UserScheme(BaseModel):
    username: str
    password: str
    email: EmailStr

    @field_validator("username")
    @classmethod
    def is_valid_username(cls, v):
        if len(v) < 5:
            raise ValueError("Username must be longer than 5 characters.")
        forbidden = set("@-.!'?*)(/{}%+^&")
        if forbidden & set(v):
            raise ValueError("Username shouldn't have ant special characters.")
        return v

class MovieScheme(BaseModel):
    query: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    device: str
    os: str
    country: str
    city: str
    created_at: str
    last_seen: str
    
    # Optional filtering out IP, memory, hostname for security
    
class MovieResponse(BaseModel):
    id: int
    tmdb_id: int
    title: str
    overview: Optional[str] = None
    genre_ids: str
    status: str
    vote_average: Optional[str] = None

class WatchedMovieResponse(BaseModel):
    id: int
    title: str
    status: str
    watched_at: str

# API wrapping responses
class APIResponseUser(BaseModel):
    success: bool
    data: dict[str, UserResponse]

class APIResponseUsersList(BaseModel):
    success: bool
    data: dict[str, List[UserResponse]]

class APIResponseWatchedMoviesList(BaseModel):
    success: bool
    data: dict[str, List[WatchedMovieResponse]]

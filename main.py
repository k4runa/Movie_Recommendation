from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from services.database import (
    logger,
    UserAlreadyExists,
    UserNotFoundError,
    MovieAlreadyExists,
)
from routers import auth, users, movies

app = FastAPI(title="Movie Recommendation API")

# Mount Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(movies.router)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    logger.info(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(UserNotFoundError)
async def user_not_found_handler(request: Request, exc: UserNotFoundError):
    logger.warning(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=404, content={"detail": "User not found"})


@app.exception_handler(UserAlreadyExists)
async def user_exists_handler(request: Request, exc: UserAlreadyExists):
    logger.warning(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=409, content={"detail": "User already exists."})


@app.exception_handler(MovieAlreadyExists)
async def movie_exists_handler(request: Request, exc: MovieAlreadyExists):
    logger.warning(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=409, content={"detail": "Movie already exists"})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"{request.method} {request.url} -> {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# 🎬 CineWave: Movie Recommendation APP

CineWave is a high-performance, asynchronous RESTful API built with FastAPI. It allows users to track their personal movie collections and receive AI-powered recommendations based on their watching history.

## 🚀 Key Features

-   **Fully Asynchronous:** Built on `FastAPI` and `SQLAlchemy (Async)` with `asyncpg` for non-blocking database operations.
-   **PostgreSQL Support:** Production-ready database integration, fully containerized with `Docker Compose`.
-   **Dual-AI Fallback:** Powered by `Google Gemini` (Primary) and `Groq/Llama-3` (Fallback). If one provider hits a quota limit, the system automatically switches to the alternative.
-   **TMDB Integration:** Real-time movie data search and discovery using `httpx`.
-   **JWT Authentication:** Secure user management and token-based authentication.
-   **Production Infrastructure:** Health-checked Docker containers for both the API and the Database.

## 🛠 Tech Stack

-   **Backend:** FastAPI, Python 3.10+
-   **Database:** PostgreSQL 16
-   **ORM:** SQLAlchemy 2.0 (Async)
-   **Async HTTP:** httpx
-   **AI Providers:** Google Gemini SDK, Groq SDK
-   **Deployment:** Docker, Docker Compose

## 🚦 Quick Start

### 1. Prerequisites
-   Docker and Docker Compose installed.
-   TMDB API Key.
-   Gemini and/or Groq API Keys.

### 2. Environment Setup
Rename `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

### 3. Run with Docker
```bash
docker-compose up -d --build
```
The API will be available at `http://localhost:8000`.  
Explore the interactive docs at `http://localhost:8000/docs`.

## 🧪 Testing
The project includes a comprehensive test suite using `pytest`.
```bash
pytest
```

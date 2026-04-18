# 🎬 CineWave: Movie Recommendation APP

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-0064a5.svg)
![Docker](https://img.shields.io/badge/Docker-27.0+-blue.svg)
![JWT](https://img.shields.io/badge/JWT-auth-green.svg)
![API](https://img.shields.io/badge/REST-API-orange.svg)
![Async](https://img.shields.io/badge/Async-Python-blue.svg)
![AI](https://img.shields.io/badge/AI-Powered-blue.svg)

CineWave is a high-performance, asynchronous RESTful API built with FastAPI. It allows users to track their personal movie collections and receive AI-powered recommendations based on their watching history. The application also includes a vanilla JavaScript Single Page Application (SPA) frontend.

## 🚀 Key Features

- **Fully Asynchronous:** Built on `FastAPI` and `SQLAlchemy (Async)` with `asyncpg` for non-blocking database operations.
- **User-Controlled AI Features:** Users can dynamically opt-in or opt-out of AI-powered features via the Settings panel. When disabled, the app gracefully falls back to standard genre-based recommendations.
- **Modern ORM Standards:** Fully compliant with SQLAlchemy 2.0+ utilizing modern `Mapped` and `mapped_column` type hinting.
- **Dual-AI Fallback:** Powered by the new `Google GenAI SDK` (Primary) and `Groq/Llama-3` (Fallback). If one provider hits a quota limit, the system automatically switches to the alternative.
- **PostgreSQL Support:** Production-ready database integration managed via `Alembic` migrations.
- **JWT Authentication:** Secure user management and token-based authentication with role-based access control (Admin/User).
- **TMDB Integration:** Real-time movie data search and discovery using `httpx`.

## 🛠 Tech Stack

- **Backend:** FastAPI, Python 3.12+
- **Database:** PostgreSQL 16
- **ORM & Migrations:** SQLAlchemy 2.0 (Async), Alembic
- **Frontend:** Vanilla JS (ES5+), CSS3 (Tailwind Zinc palette inspired)
- **Async HTTP:** httpx
- **AI Providers:** Google GenAI SDK (`google-genai`), Groq SDK
- **Deployment:** Docker, Docker Compose

## 🚦 Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed.
- TMDB API Key.
- Gemini and/or Groq API Keys.

### 2. Environment Setup

Rename `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

### 3. Run with Docker

```bash
docker-compose up -d --build
```

### 4. Database Migrations

If you are running the project locally outside of Docker, ensure you run migrations:

```bash
alembic upgrade head
```

The API will be available at `http://localhost:8000`.  
Explore the interactive docs at `http://localhost:8000/docs`.
Access the frontend by visiting `http://localhost:8000/` in your browser.

## 🧪 Testing

The project includes a comprehensive test suite using `pytest`.

```bash
pytest
```

# 🎬 CineWave: AI-Powered Full-Stack Movie Ecosystem

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)
![Next.js](https://img.shields.io/badge/Next.js-15+-black.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-0064a5.svg)
![Docker](https://img.shields.io/badge/Docker-Multi--Stage-2496ED.svg)

CineWave is a high-performance, asynchronous movie tracking and recommendation platform. It features a stunning **Next.js** dashboard with a Glassmorphism design and is powered by **Eco**, a personalized AI assistant that understands your cinematic taste.

The entire application (Frontend + Backend) is seamlessly unified into a single deployment pipeline.

---

## 🚀 Key Features

- **Unified Full-Stack Architecture:** The Next.js frontend is statically exported and served directly by the FastAPI backend, eliminating CORS issues and simplifying deployment.
- **Personalized AI (Eco):** A dedicated AI persona that analyzes your movie library to provide deep insights and explain why certain movies are recommended.
- **Glassmorphism UI:** A premium, state-of-the-art dashboard built with Next.js, Framer Motion, and Tailwind CSS.
- **Robust Database Management:** Powered by PostgreSQL and SQLAlchemy 2.0 (Async), with schema versioning strictly managed by **Alembic**.
- **Multi-Stage Docker Pipeline:** A highly optimized Docker build that securely compiles the Node.js frontend and packages it into a lightweight Python container.
- **Dual-Layer Caching:** Zustand-based caching on the client and Custom Async TTL Cache on the server protect against API rate limits and optimize CPU load.

## 🛠 Tech Stack

- **Backend:** FastAPI, Python 3.12+
- **Database:** PostgreSQL 16+ (Asyncpg & Psycopg2)
- **Migrations:** Alembic
- **Frontend:** Next.js 15, TypeScript, Tailwind CSS, Zustand, Framer Motion
- **AI Providers:** Google Gemini (Primary), Groq/Llama-3 (Fallback)

---

## 🚦 Quick Start (Local Development)

### 1. Environment Setup

Copy the environment template and fill in your API keys (TMDB, Gemini/Groq):

```bash
cp .env.example .env
```

> **Note:** Set `INITIAL_ADMIN_USERNAME` and `INITIAL_ADMIN_PASSWORD` in your `.env` to automatically seed an admin account upon startup.

### 2. Start the Database

```bash
# Start the PostgreSQL database container
docker-compose up -d cinewave_db
```

### 3. Run Backend & Migrations

```bash
# Install dependencies
pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Start the API server
uvicorn main:app --reload
```

### 4. Run Frontend

```bash
cd web
npm install
npm run dev
```

The API runs on `http://localhost:8000` and the frontend runs on `http://localhost:3000`.

---

## 🐳 Production Deployment (Docker)

CineWave uses a **Multi-Stage Docker Build**. Docker will first compile the Next.js frontend into static files, then copy them into a lightweight Python container. The startup script (`start.sh`) will automatically run Alembic migrations before launching the application.

To deploy the entire stack (Database + Unified API/Frontend):

```bash
# Build and start the production containers
docker-compose up -d --build
```

Access the live application at: `http://localhost:8000/ui/`

---

## 🛡️ Security & Performance Hardening

CineWave is engineered for production-grade reliability:

- **Server-Side Token Revocation:** JWTs are immediately invalidated upon logout using a server-side async cache blacklist.
- **Optimized Indices:** Database tables use targeted foreign-key indexing (O(1) lookups) to prevent full-table scans.
- **Connection Pool Tuning:** Strict connection limits fit within low-memory environments (e.g., 512MB RAM VPS).
- **Atomic Operations:** Custom `@transaction` decorators ensure that library updates and deletions are always safe and consistent.

---

_CineWave — Your Cinematic Journey, Optimized._

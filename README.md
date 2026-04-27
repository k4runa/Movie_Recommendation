# ecofil

<p align="center">
  <img src="./.images/hero.png" alt="ecofil Hero" width="100%" />
</p>

ecofil is a movie tracking and recommendation system built with FastAPI and Next.js. It features a personalized AI assistant that provides movie suggestions based on your library and preferences.

## Features

- **Movie Tracking:** Manage your library of movies, anime, and shows with simple tracking tools.
- **AI Recommendations:** A personalized assistant that analyzes your taste and explains why certain movies are suggested.
- **Social Features:** Connect with users who have similar tastes, and communicate through a real-time messaging system.

<p align="center">
  <img src="./.images/eco-ai.png" alt="Eco AI" width="32%" />
  <img src="./.images/daily-picks.png" alt="Daily Picks" width="32%" />
  <img src="./.images/my-collections.png" alt="Collections" width="32%" />
</p>

- **Privacy Focused:** Control what information is visible on your profile, including your bio, age, location, and library.
- **Clean Interface:** A high-contrast, professional dashboard designed for clarity and ease of use.
- **Secure Backend:** Asynchronous FastAPI architecture with identity-based access control and secure authentication.

## Tech Stack

- **Backend:** FastAPI, Python 3.12+
- **Database:** PostgreSQL 16+ (SQLAlchemy Async)
- **Migrations:** Alembic
- **Frontend:** Next.js, TypeScript, Tailwind CSS
- **AI Integration:** Google Gemini, Groq (Llama-3)

## Quick Start

### 1. Environment Setup

Copy the environment template and provide your API keys (TMDB, Gemini/Groq):

```bash
cp .env.example .env
```

### 2. Database

Start the PostgreSQL database container:

```bash
docker-compose up -d ecofil_db
```

### 3. Backend & Migrations

```bash
# Install dependencies
pip install -r requirements.txt

# Apply migrations
alembic upgrade head

# Start the server
uvicorn main:app --reload
```

### 4. Frontend

```bash
cd web
npm install
npm run dev
```

The API is available at `http://localhost:8000` and the frontend at `http://localhost:3000`.

## Production Deployment

ecofil uses a multi-stage Docker build to package both the backend and the frontend into a single container.

```bash
# Build and start production containers
docker-compose up -d --build
```

Access the application at `http://localhost:8000/ui/`

## Infrastructure Notes

- **Identity Management:** Access control is managed through JWT tokens, ensuring secure and direct ownership of data.
- **Performance:** Database queries are optimized with targeted indexing and async connection pooling.
- **Schema Management:** All database changes are strictly versioned with Alembic to ensure consistency across environments.
- **Static Hosting:** The Next.js frontend is served directly by the FastAPI backend to simplify the architecture.

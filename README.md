# Movie Recommendation API

<div align="center">

![GitHub last commit](https://img.shields.io/github/last-commit/k4runa/Movie_Recommendation?style=for-the-badge&color=5D5DFF)
![GitHub top language](https://img.shields.io/github/languages/top/k4runa/Movie_Recommendation?style=for-the-badge&color=5D5DFF)
![GitHub repo size](https://img.shields.io/github/repo-size/k4runa/Movie_Recommendation?style=for-the-badge&color=5D5DFF)
![Python Version](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688?style=for-the-badge&logo=fastapi&logoColor=white)

</div>

---

A production-ready RESTful API for tracking personal movie collections and generating genre-based recommendations using data from [TMDB](https://www.themoviedb.org/). Features a modern, high-performance dark-themed SPA (Single Page Application) built with vanilla JavaScript.

---

## Features

| Category                  | Details                                                                                                                     |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Authentication**        | Secure JWT Bearer tokens via `PyJWT` + `bcrypt`. OAuth2-compatible flow.                                                    |
| **User Management**       | Full CRUD with soft-delete. Automatic role assignment (`admin` vs `user`).                                                  |
| **Collection Tracking**   | Real-time TMDB search. Add/Remove movies to your "Watched" or "To Watch" list.                                              |
| **Recommendation Engine** | Genre-based discovery algorithm. Analyzes your watch history categories and discovers similar trending titles via TMDB API. |
| **Ownership & Privacy**   | Strict ownership enforcement. Users can only access and modify their own collections.                                       |
| **Admin Oversight**       | Powerful admin dashboard to manage users, view device metadata, and enforce community standards.                            |
| **Responsive UI**         | Flicker-free Single Page App (SPA) with a premium Zinc dark theme and smooth transitions.                                   |
| **Infrastructure**        | Fully containerized with Docker. Zero-config deployment via Docker Compose.                                                 |
| **Test Suite**            | Comprehensive E2E tests using `pytest` and `TestClient`.                                                                    |

---

## Project Structure

```text
.
├── main.py                     # App entry point & global configurations
├── alembic/                    # Database schema migration framework
├── routers/                    # API route definitions (Modularized)
│   ├── auth.py                 # JWT issuance & Login
│   ├── users.py                # User profiles & Admin operations
│   └── movies.py               # Movie tracking & Recommendations
├── services/                   # Business logic & Core engines
│   ├── auth.py                 # Token logic & Password hashing
│   ├── database.py             # SQLAlchemy models & CRUD managers
│   ├── schemas.py              # Pydantic validation & Serialization
│   ├── deps.py                 # Dependency injection containers
│   └── tmdb.py                 # TMDB API integration layer
├── frontend/                   # Modern Web SPA
│   ├── index.html              # Reactive HTML shell
│   ├── css/style.css           # Premium dark theme design system
│   └── js/app.js               # Tab-based SPA logic & API client
├── tests/                      # Automated test suite
└── Dockerfile                  # Production container definition
```

---

## Tech Stack

- **Backend:** FastAPI (Python 3.10+)
- **ORM / DB:** SQLAlchemy 2.0 with SQLite
- **Migrations:** Alembic
- **Frontend:** Vanilla JS, CSS3, Semantic HTML5
- **Security:** JWT (JSON Web Tokens) & Bcrypt
- **DevOps:** Docker, Docker Compose

---

## Quick Start

### 1. Requirements

Ensure you have a **TMDB API Key** ([Get one here](https://www.themoviedb.org/settings/api)).

### 2. Docker Setup (Recommended)

```bash
git clone https://github.com/k4runa/Movie_Recommendation.git
cd Movie_Recommendation

# Create .env and paste your credentials
cp .env.example .env  # If example exists, else create manually

# Start the stack
docker-compose up -d --build
```

### 3. Localization

The API will be available at `http://localhost:8000`.

- **Web UI:** [http://localhost:8000/ui](http://localhost:8000/ui)
- **Interactive Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Development & Testing

**Run Tests:**

```bash
python -m pytest tests/ -v
```

**Apply Migrations:**

```bash
alembic upgrade head
```

---

## Admin Panel

Register with the username `admin` to gain automatic administrative privileges. You can then access the **Admin Panel** tab in the UI to manage the user base and view system analytics.

---

<div align="center">
  <sub>Built for Movie Lovers.</sub>
</div>

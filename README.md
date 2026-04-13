# CineWave — AI Movie Recommendation API

A production-grade RESTful API for tracking movies and generating personalized recommendations powered by [TMDB](https://www.themoviedb.org/). Built with **FastAPI**, secured with **JWT authentication**, managed with **Alembic migrations**, and shipped with a custom dark-themed **web interface**.

---

## Features

| Category | Details |
|---|---|
| **Authentication** | JWT Bearer tokens via `PyJWT` + `bcrypt` password hashing. OAuth2-compatible login endpoint. |
| **User Management** | Registration, profile retrieval, soft-delete, field-level updates. Device fingerprint & geolocation metadata collected at signup for admin analytics. |
| **Movie Tracking** | Search TMDB by title, add movies to your personal collection, remove them at will. |
| **Smart Recommendations** | Genre-based discovery — analyses your top 5 most-watched genres, queries TMDB's `/discover` endpoint, filters out already-tracked movies, and shuffles results for variety on every page load. |
| **Admin Panel** | Role-based access control (`admin` / `user`). Admin users can view all registered users' device metadata (OS, location, join date) and ban accounts via the web UI. |
| **Pagination** | `skip` / `limit` query params on all list endpoints. |
| **Database Migrations** | Alembic integration for zero-downtime, zero-data-loss schema evolution. |
| **Web UI** | Vanilla JS single-page application with a true dark theme (Zinc palette), tab-based navigation, and lazy-loaded cached data to eliminate flicker. |
| **Containerized** | Dockerfile + docker-compose for one-command deployment. |
| **Tested** | End-to-end pytest suite covering the full auth lifecycle and ownership enforcement. |

---

## Project Structure

```
CineWave/
├── main.py                     # FastAPI app bootstrap & global exception handlers
├── alembic/                    # Database migration framework
│   ├── env.py                  # Alembic environment config (loads ORM metadata)
│   └── versions/               # Auto-generated migration scripts
├── routers/
│   ├── __init__.py             # Router package exports
│   ├── auth.py                 # POST /login — JWT token issuance
│   ├── users.py                # CRUD /users — registration, profile, admin list
│   └── movies.py               # CRUD /movies + GET /recommendations
├── services/
│   ├── auth.py                 # JWT creation, validation & password verification
│   ├── database.py             # ORM models (User, Movies, WatchedMovies) & managers
│   ├── schemas.py              # Pydantic request/response models (data whitelist)
│   ├── deps.py                 # Singleton manager instances (dependency injection)
│   └── tmdb.py                 # TMDB API integration (search & discover)
├── frontend/
│   ├── index.html              # SPA shell — auth form, dashboard tabs, admin table
│   ├── css/style.css           # Design system — true dark theme (Zinc palette)
│   └── js/app.js               # Client-side logic — auth, data fetching, caching
├── tests/
│   └── test_auth.py            # E2E test: register → login → access → ownership
├── Dockerfile                  # Container image definition
├── docker-compose.yml          # Single-service orchestration
├── alembic.ini                 # Alembic configuration (DB URL, logging)
├── requirements.txt            # Pinned Python dependencies (production only)
├── .env                        # Secrets (not committed — see template below)
├── .gitignore                  # Git exclusions
└── .dockerignore               # Docker build context exclusions
```

---

## Quick Start

### Option 1 — Docker (Recommended)

```bash
git clone https://github.com/k4runa/Movie_Recommendation.git
cd Movie_Recommendation
```

Create a `.env` file in the project root:

```env
DB_PATH=database/database.db
JWT_SECRET_KEY=your_super_secret_jwt_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120
API_KEY=your_tmdb_api_key_here
```

Build and run:

```bash
docker-compose up -d --build
```

### Option 2 — Local Development

```bash
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## Access Points

| URL | Description |
|---|---|
| `http://localhost:8000/ui` | **Web Interface** — Full SPA with auth, tracking, recommendations, and admin panel |
| `http://localhost:8000/docs` | **Swagger UI** — Interactive API documentation with "Try it out" |
| `http://localhost:8000/redoc` | **ReDoc** — Alternative read-only API documentation |

---

## API Endpoints

### Authentication
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/login` | No | Authenticate and receive a JWT |

### Users
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/users` | No | Register a new account |
| `GET` | `/users` | Admin | List all users (admin-only) |
| `GET` | `/users/{username}` | Owner | Get own profile |
| `GET` | `/users/id/{id}` | No | Get user by numeric ID |
| `DELETE` | `/users/{username}` | Owner | Soft-delete own account |
| `PATCH` | `/users/{username}` | Owner | Update a profile field |

### Movies
| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/movies/{username}/watched` | Owner | List tracked movies (paginated) |
| `POST` | `/movies/{username}` | Owner | Track a new movie (TMDB search) |
| `DELETE` | `/movies/{username}/{title}` | Owner | Remove a tracked movie |
| `GET` | `/movies/recommendations/{username}` | Owner | Get personalized recommendations |

---

## Database Migrations

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/). You never need to delete your database when the schema evolves.

```bash
# After modifying ORM models in services/database.py:
python -m alembic revision --autogenerate -m "describe your change"

# Apply all pending migrations:
python -m alembic upgrade head

# Roll back one migration:
python -m alembic downgrade -1
```

---

## Admin Access

Register with the username **`admin`** to receive automatic admin privileges. The admin panel provides:

- Full user metadata table (device, OS, city/country, join date)
- User ban (soft-delete) with confirmation dialogs
- Protected by role-based access on both the API and UI layers

---

## Testing

```bash
python -m pytest tests/ -v
```

The test suite covers:
- User registration (POST /users)
- Login and JWT issuance (POST /login)
- Protected route access with a valid token
- Ownership enforcement (accessing another user's data → 403)

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DB_PATH` | Yes | `database/database.db` | Path to the SQLite database file |
| `JWT_SECRET_KEY` | Yes | — | HMAC signing key for JWT tokens |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `120` | Token TTL in minutes |
| `API_KEY` | Yes | — | TMDB API key ([get one here](https://www.themoviedb.org/settings/api)) |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.135 |
| ORM | SQLAlchemy 2.x |
| Database | SQLite |
| Migrations | Alembic |
| Auth | PyJWT + bcrypt |
| External API | TMDB v3 |
| Frontend | Vanilla JS / CSS (SPA) |
| Testing | Pytest |
| Deployment | Docker + docker-compose |

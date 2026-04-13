# Movie Recommendation API 🎬

A modern, fast, and feature-rich RESTful API for managing users, tracking their watched movies, and generating personalized movie recommendations based on their watching habits. Built with FastAPI and powered by the TMDB (The Movie Database) API.

## Features ✨

- **JWT Authentication**: Secure user registration and login endpoints utilizing Bearer passing. 
- **User Management**: Add, view, update, and soft-delete users. Automatic gathering of connected device properties for analytics.
- **Movies & Tracking**: Users can search for movies natively through TMDB integration, saving them to their watched list.
- **Personalized Recommendations**: Intelligent fetching of similar movies based on users' most watched genres.
- **Pagination**: Built-in limit/offset capabilities on core routes.
- **Dockerized**: Fully portable container packaging.

## Installation 🚀

### Option 1: Using Docker (Recommended)

1. Clone the repository
```bash
git clone https://github.com/k4runa/Movie_Recommendation.git
cd Movie_Recommendation
```

2. Create a `.env` file in the root directory:
```env
DB_PATH=database/database.db
JWT_SECRET_KEY=your_super_secret_jwt_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120
API_KEY=your_tmdb_api_key_here
```

3. Build and run the containers:
```bash
docker-compose up -d --build
```

### Option 2: Local Installation

1. Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure the `.env` file (same as above).

3. Run the development server:
```bash
uvicorn main:app --reload
```

## API Documentation 📚

Once the server is running, navigate to the auto-generated Swagger UI or ReDoc to interact with the endpoints interactively:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Testing 🧪

A comprehensive Pytest suite is included for endpoint validation:
```bash
python -m pytest tests/
```

## Technologies Used 🛠️

- **FastAPI** -> Web Framework
- **SQLAlchemy** -> ORM
- **SQLite** -> Database
- **PyJWT & Passlib / Bcrypt** -> Security & Hashing
- **Pytest** -> Testing Engine
- **Docker** -> Containerization

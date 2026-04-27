import asyncio
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path to import services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.database import User, Movies, WatchedMovies, init_database, _session_maker
from sqlalchemy import select
import bcrypt

async def seed_data():
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://ecofil:[EMAIL_ADDRESS]:5432/ecofil_db")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    
    init_database(database_url)
    
    import services.database
    from sqlalchemy import delete
    async with services.database._session_maker() as session:
        # Cleanup first
        usernames = ["cinephile_max", "horror_fan", "scifi_geek"]
        await session.execute(delete(User).where(User.username.in_(usernames)))
        await session.commit()

        # 1. Create Dummy Users
        dummies = [
            {"username": "cinephile_max", "email": "max@example.com", "movies": [27205, 157336, 36865]}, # Inception, Interstellar, Haruhi
            {"username": "horror_fan", "email": "horror@example.com", "movies": [135397, 10625]}, # Jurassic World, Interview with the Vampire
            {"username": "anime_lover", "email": "anime@example.com", "movies": [36865, 129, 4935]}, # Haruhi, Spirited Away, Ranma 1/2
        ]
        
        for d in dummies:
            # Check if exists
            stmt = select(User).where(User.username == d["username"])
            res = await session.execute(stmt)
            if res.scalar_one_or_none():
                print(f"User {d['username']} already exists.")
                continue
            
            hashed = bcrypt.hashpw("password123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            user = User(
                username=d["username"],
                email=d["email"],
                password=hashed,
                role="user",
                avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={d['username']}",
                created_at=datetime.now(timezone.utc).isoformat(),
                last_seen=datetime.now(timezone.utc).isoformat()
            )
            session.add(user)
            await session.flush()
            
            # Add movies
            for tmdb_id in d["movies"]:
                movie = Movies(
                    user_id=user.id,
                    tmdb_id=tmdb_id,
                    title=f"Movie {tmdb_id}",
                    genre_ids="12,18,878", # Adventure, Drama, Sci-Fi
                )
                session.add(movie)
                await session.flush()
                
                watched = WatchedMovies(
                    user_id=user.id,
                    movie_id=movie.id,
                    title=movie.title,
                    status="Watched"
                )
                session.add(watched)
        
        await session.commit()
        print("Successfully seeded dummy users for social testing!")

if __name__ == "__main__":
    asyncio.run(seed_data())

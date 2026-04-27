import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from services.database import Base, db_url

async def reset_db():
    print(f"Connecting to {db_url}...")
    engine = create_async_engine(db_url)
    
    async with engine.begin() as conn:
        print("Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Database reset complete.")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_db())

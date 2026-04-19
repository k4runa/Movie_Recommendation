import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def reset_alembic():
    """
    Drops the alembic_version table to resolve migration mismatch errors.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found. Skipping reset.")
        return

    # Handle Render's postgres:// vs postgresql+asyncpg://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)

    print(f"🔄 Connecting to database to reset migration version...")
    engine = create_async_engine(database_url)
    
    try:
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE;"))
        print("✅ Successfully dropped alembic_version table.")
    except Exception as e:
        print(f"⚠️ Error resetting alembic: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_alembic())

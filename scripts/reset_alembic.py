import os
from sqlalchemy import create_engine, text

def wipe_and_reset_db():
    """
    KÖKTEN ÇÖZÜM: Drops the entire public schema and recreates it.
    This wipes ALL tables (users, movies, alembic_version, etc.) 
    to allow a perfectly clean start for Alembic.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found. Skipping wipe.")
        return

    # Render uses postgres://, SQLAlchemy sync engine needs postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    print(f"🧨 Connecting to database to WIPE EVERYTHING...")
    
    try:
        engine = create_engine(database_url)
        with engine.begin() as conn:
            # Drop the public schema and recreate it - the most robust 'wipe' method
            conn.execute(text("DROP SCHEMA public CASCADE;"))
            conn.execute(text("CREATE SCHEMA public;"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
            # For some cloud DBs, the owner might need extra permissions
            conn.execute(text("COMMENT ON SCHEMA public IS 'standard public schema';"))
        print("✅ DATABASE WIPED CLEAN. Ready for fresh migration.")
    except Exception as e:
        print(f"⚠️ Error wiping database: {e}")

if __name__ == "__main__":
    wipe_and_reset_db()

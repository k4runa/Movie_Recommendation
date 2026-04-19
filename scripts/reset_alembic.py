import os
from sqlalchemy import create_engine, text

def reset_alembic():
    """
    Drops the alembic_version table using a sync engine to resolve migration mismatches.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found. Skipping reset.")
        return

    # Render uses postgres://, SQLAlchemy sync engine needs postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    print(f"🔄 Connecting to database (Sync) to reset migration version...")
    
    try:
        # Use a standard sync engine (uses psycopg2-binary which is already in requirements)
        engine = create_engine(database_url)
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE;"))
        print("✅ Successfully dropped alembic_version table.")
    except Exception as e:
        print(f"⚠️ Error resetting alembic: {e}")

if __name__ == "__main__":
    reset_alembic()

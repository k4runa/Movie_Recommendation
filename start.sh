#!/bin/bash
set -e

# start.sh — Optimized for production (512MB RAM)
# This script runs when the container or web service starts.

echo "🚀 Starting CineWave Production Environment..."

# 1. Sync database migrations
# We force-reset the alembic version to avoid 'Can't locate revision' errors on Render.
echo "Resetting database migration state..."
python scripts/reset_alembic.py
echo "Synchronizing database migrations..."
alembic upgrade head

# 2. Start the application with Gunicorn
# We use a single worker for 512MB RAM environments to ensure stability.
echo "Starting CineWave API (Gunicorn)..."
exec gunicorn -w ${WEB_CONCURRENCY:-1} -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:${PORT:-8000} --access-logfile -

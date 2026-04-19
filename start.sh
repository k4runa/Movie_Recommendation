#!/bin/bash
set -e

# start.sh — Optimized for production (512MB RAM)
# This script runs when the container or web service starts.

echo "🚀 Starting CineWave Production Environment..."

# 1. Sync database migrations
# If the DB is out of sync (e.g. looking for a missing revision), we stamp it to the current head.
echo "Synchronizing database migrations..."
alembic stamp 0001_initial || echo "Stamp failed, continuing..."
alembic upgrade head

# 2. Start the application with Gunicorn
# We use a single worker for 512MB RAM environments to ensure stability.
echo "Starting CineWave API (Gunicorn)..."
exec gunicorn -w ${WEB_CONCURRENCY:-1} -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:${PORT:-8000} --access-logfile -

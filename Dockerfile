# ==========================================================================
# CineWave API — Dockerfile
# ==========================================================================
# Multi-purpose container image for the FastAPI application.
# Includes all Python dependencies, the frontend SPA, and Alembic
# migration tooling.
#
# Build:  docker build -t cinewave-api .
# Run:    docker run -p 8000:8000 --env-file .env cinewave-api
# ==========================================================================

FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
# so that container logs appear in real time.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies first (leverages Docker layer caching — only
# re-installed when requirements.txt changes).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and frontend assets
COPY . .

# Expose the default uvicorn port
EXPOSE 8000

# Launch the ASGI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

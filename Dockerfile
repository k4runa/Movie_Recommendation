# CineWave API — Multi-Stage Dockerfile
# Builds the Next.js frontend and the FastAPI backend into a single lean image.

# --- Stage 1: Build Frontend ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/web

# Install dependencies
COPY web/package*.json ./
RUN npm ci

# Copy source and build static files
COPY web/ ./
RUN npm run build

# --- Stage 2: Build Backend & Final Image ---
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install backend dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Copy built frontend static files from Stage 1 into the backend's static directory
COPY --from=frontend-builder /app/web/out /app/frontend

EXPOSE 8000

# Ensure the startup script is executable
RUN chmod +x start.sh

# Start using the custom startup script (runs Alembic then Gunicorn)
CMD ["./start.sh"]

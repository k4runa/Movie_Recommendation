#!/bin/bash

# 1. Veritabanı tablolarını en son sürüme güncelle (Alembic)
echo "Running database migrations..."
alembic upgrade head

# 2. Uygulamayı Gunicorn ile başlat (Üretim seviyesi performans için)
echo "Starting CineWave API..."
exec gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT

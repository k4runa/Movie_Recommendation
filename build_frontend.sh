#!/bin/bash

# Exit on error
set -e

echo "🚀 Building Next.js Frontend..."

cd web

# 1. Build Next.js
npm run build

# 2. Clear old frontend files in the root if they exist
# We'll keep the 'frontend' folder as the target for FastAPI
cd ..
mkdir -p frontend
rm -rf frontend/*

# 3. Copy Next.js static output to the 'frontend' folder
# Next.js 'export' output is in 'web/out'
cp -r web/out/* frontend/

echo "✅ Frontend Build Complete! Static files moved to /frontend"

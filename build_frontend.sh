#!/bin/bash
set -e

# build_frontend.sh — Robust build script for Render
echo "🚀 Starting Robust Frontend Build Process..."

if [ -d "web" ]; then
    cd web
    
    # Ensure dependencies are installed locally in this environment
    echo "📦 Installing web dependencies (Double checking)..."
    npm install --no-audit --no-fund
    
    echo "🏗️ Running Next.js build via npx..."
    # Using npx ensures we find the 'next' binary even if it's not in the PATH
    npx next build
    
    cd ..
    echo "📂 Copying build output to /frontend static directory..."
    mkdir -p frontend
    rm -rf frontend/*
    
    if [ -d "web/out" ]; then
        cp -r web/out/* frontend/
        echo "✅ Frontend build successfully deployed to /frontend"
    else
        echo "❌ Error: 'web/out' directory not found after build."
        exit 1
    fi
else
    echo "❌ Error: 'web' directory not found. Skipping build."
    exit 1
fi

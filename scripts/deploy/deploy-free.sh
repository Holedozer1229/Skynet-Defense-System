#!/bin/bash
# SphinxSkynet Free Deployment Script
set -e

echo "🚀 SphinxSkynet Gasless Blockchain - Free Deploy"
echo "================================================"

# Detect deployment target
if command -v railway &> /dev/null; then
    echo "✅ Deploying to Railway..."
    railway up
elif command -v flyctl &> /dev/null; then
    echo "✅ Deploying to Fly.io..."
    flyctl deploy
else
    echo "⚠️  No cloud CLI found. Starting locally..."
    pip install -r requirements.txt
    uvicorn sphinx_os.api.main:app --host 0.0.0.0 --port 8000
fi

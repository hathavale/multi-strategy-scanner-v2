#!/bin/bash

# Heroku Deployment Script for Multi-Strategy Options Scanner

echo "🚀 Multi-Strategy Options Scanner - Heroku Deployment"
echo "========================================================"

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI not found. Please install it first:"
    echo "   https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

echo "✅ Heroku CLI found"

# Check if logged in
if ! heroku auth:whoami &> /dev/null; then
    echo "🔐 Please login to Heroku:"
    heroku login
fi

# Ask for app name
read -p "Enter Heroku app name (leave empty for auto-generated): " APP_NAME

# Create app
if [ -z "$APP_NAME" ]; then
    echo "📦 Creating new Heroku app with auto-generated name..."
    heroku create
else
    echo "📦 Creating new Heroku app: $APP_NAME..."
    heroku create "$APP_NAME"
fi

# Get app name
APP_NAME=$(heroku apps:info --json | python3 -c "import sys, json; print(json.load(sys.stdin)['app']['name'])")
echo "✅ App created: $APP_NAME"

# Add PostgreSQL
echo "🗄️  Adding PostgreSQL database..."
heroku addons:create heroku-postgresql:mini --app "$APP_NAME"
echo "✅ Database added"

# Set environment variables
echo "🔧 Setting environment variables..."

# Generate secret key
SECRET_KEY=$(openssl rand -base64 32)
heroku config:set SECRET_KEY="$SECRET_KEY" --app "$APP_NAME"

# Set production environment
heroku config:set FLASK_ENV=production --app "$APP_NAME"
heroku config:set FLASK_DEBUG=False --app "$APP_NAME"

# Ask for Alpha Vantage API key
read -p "Enter your Alpha Vantage API key: " API_KEY
heroku config:set ALPHAVANTAGE_API_KEY="$API_KEY" --app "$APP_NAME"

# Optional settings
heroku config:set MAX_SYMBOLS_PER_SCAN=10 --app "$APP_NAME"
heroku config:set ENABLE_RATE_LIMITING=True --app "$APP_NAME"
heroku config:set RATE_LIMIT_PER_MINUTE=60 --app "$APP_NAME"

echo "✅ Environment variables configured"

# Deploy
echo "📤 Deploying application..."
git push heroku main || git push heroku master:main

# Initialize database
echo "🗄️  Initializing database..."
heroku run python backend/database/init_db.py --app "$APP_NAME"

echo ""
echo "=========================================================="
echo "✅ Deployment Complete!"
echo "=========================================================="
echo "🌐 Your app is available at: https://$APP_NAME.herokuapp.com"
echo ""
echo "Useful commands:"
echo "  View logs:     heroku logs --tail --app $APP_NAME"
echo "  Open app:      heroku open --app $APP_NAME"
echo "  View config:   heroku config --app $APP_NAME"
echo "  Restart:       heroku restart --app $APP_NAME"
echo ""

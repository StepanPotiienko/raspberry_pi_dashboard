#!/bin/bash

# Raspberry Pi Dashboard - Quick Start Script

echo "🥧 Starting Raspberry Pi Dashboard..."
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "✓ Activating virtual environment..."
    source .venv/bin/activate
else
    echo "⚠️  Virtual environment not found. Creating one..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "✓ Installing dependencies..."
    pip install -r requirements.txt
fi

# Run migrations if needed
echo "✓ Checking database migrations..."
python manage.py migrate --no-input

# Collect static files (for production)
# python manage.py collectstatic --no-input

# Start the server
echo "✓ Starting Django development server..."
echo ""
echo "================================================"
echo "Dashboard will be available at:"
echo "  http://localhost:8080"
echo "  http://$(hostname -I | awk '{print $1}'):8080"
echo "================================================"
echo ""
python manage.py runserver 0.0.0.0:8080

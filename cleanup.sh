#!/bin/bash

# Remove unnecessary files
rm -f devicedb.sqlite3
rm -f db.sqlite3
rm -f migrate.sh
rm -f create_test_user.py
rm -rf device_management/
rm -rf code/
rm -rf .venv/

# Remove all __pycache__ directories
find . -type d -name "__pycache__" -exec rm -r {} +

# Remove all .pyc files
find . -name "*.pyc" -delete

# Create necessary directories
mkdir -p static
mkdir -p media
mkdir -p logs

# Set proper permissions
chmod 755 manage.py
chmod 644 requirements.txt
chmod 644 .env.production 
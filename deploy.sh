#!/bin/bash

# Activate virtual environment (create if doesn't exist)
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create superuser if needed (comment out if not needed)
# python manage.py create_admin

# Set proper permissions
chmod -R 755 .
find . -type f -exec chmod 644 {} \;
chmod 755 manage.py
chmod 755 deploy.sh

# Create necessary directories with proper permissions
mkdir -p logs
mkdir -p media
mkdir -p static
chmod -R 755 logs
chmod -R 755 media
chmod -R 755 static 
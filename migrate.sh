#!/bin/bash

# Migration Script for Device Management System
# This script helps migrate the system to a new machine

# Configuration
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
DB_NAME="db.sqlite3"
PROJECT_DIR="device_management"

# Create backup directory
echo "Creating backup directory..."
mkdir -p $BACKUP_DIR

# Backup database
echo "Backing up database..."
cp $DB_NAME $BACKUP_DIR/

# Backup project files
echo "Backing up project files..."
cp -r $PROJECT_DIR $BACKUP_DIR/
cp -r login $BACKUP_DIR/
cp -r dashboard $BACKUP_DIR/
cp manage.py $BACKUP_DIR/
cp requirements.txt $BACKUP_DIR/
cp database_schema.sql $BACKUP_DIR/

# Create migration instructions
echo "Creating migration instructions..."
cat > $BACKUP_DIR/MIGRATION_INSTRUCTIONS.txt << EOL
Device Management System Migration Instructions
============================================

1. Prerequisites:
   - Python 3.x installed
   - pip installed
   - Virtual environment (recommended)

2. Setup Steps:
   a. Create a new virtual environment:
      python -m venv venv
      source venv/bin/activate  # On Windows: venv\Scripts\activate

   b. Install requirements:
      pip install -r requirements.txt

   c. Initialize the database:
      python manage.py migrate

   d. Create superuser (optional):
      python manage.py createsuperuser

3. Files to Copy:
   - Copy all files from this backup directory to the new machine
   - Make sure to maintain the same directory structure

4. Database:
   - The database file (db.sqlite3) is included in this backup
   - Copy it to the same location as in the original setup

5. Start the Server:
   python manage.py runserver

Note: Make sure to update any configuration files if the new environment
has different settings (e.g., database paths, allowed hosts, etc.)
EOL

# Create archive
echo "Creating archive..."
tar -czf device_management_backup.tar.gz $BACKUP_DIR

# Cleanup
echo "Cleaning up..."
rm -rf $BACKUP_DIR

echo "Migration package created: device_management_backup.tar.gz"
echo "Please copy this file to the new machine and follow the instructions in MIGRATION_INSTRUCTIONS.txt" 
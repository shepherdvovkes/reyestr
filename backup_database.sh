#!/bin/bash
# Script to backup PostgreSQL database
# Usage: ./backup_database.sh [backup_directory]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Database connection parameters (can be overridden by environment variables)
DB_HOST=${DB_HOST:-127.0.0.1}
DB_PORT=${DB_PORT:-5433}
DB_NAME=${DB_NAME:-reyestr_db}
DB_USER=${DB_USER:-reyestr_user}
DB_PASSWORD=${DB_PASSWORD:-reyestr_password}

# Backup directory (default: ./backups)
BACKUP_DIR=${1:-./backups}
BACKUP_DIR=$(realpath "$BACKUP_DIR")

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Set password for pg_dump
export PGPASSWORD="$DB_PASSWORD"

# Generate backup filename with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/reyestr_db_backup_${TIMESTAMP}.sql"
BACKUP_FILE_COMPRESSED="$BACKUP_FILE.gz"

# Check if pg_dump is available
if ! command -v pg_dump &> /dev/null; then
    echo -e "${RED}Error: pg_dump command not found. Please install PostgreSQL client.${NC}"
    exit 1
fi

echo -e "${GREEN}Starting database backup...${NC}"
echo "Database: $DB_NAME@$DB_HOST:$DB_PORT"
echo "User: $DB_USER"
echo "Backup file: $BACKUP_FILE_COMPRESSED"
echo ""

# Perform backup
if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --verbose \
    --no-owner \
    --no-privileges \
    --format=plain \
    > "$BACKUP_FILE" 2>&1; then
    
    # Compress backup
    if command -v gzip &> /dev/null; then
        gzip "$BACKUP_FILE"
        BACKUP_FILE="$BACKUP_FILE_COMPRESSED"
        echo -e "${GREEN}✓ Backup compressed${NC}"
    fi
    
    # Get file size
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Backup completed successfully!${NC}"
    echo -e "File: ${YELLOW}$BACKUP_FILE${NC}"
    echo -e "Size: ${YELLOW}$FILE_SIZE${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # Clean up old backups (keep last 30 days)
    echo ""
    echo -e "${YELLOW}Cleaning up old backups (keeping last 30 days)...${NC}"
    find "$BACKUP_DIR" -name "reyestr_db_backup_*.sql.gz" -type f -mtime +30 -delete 2>/dev/null || true
    OLD_COUNT=$(find "$BACKUP_DIR" -name "reyestr_db_backup_*.sql.gz" -type f | wc -l)
    echo -e "${GREEN}✓ Kept $OLD_COUNT backup files${NC}"
    
    exit 0
else
    echo -e "${RED}✗ Backup failed${NC}"
    # Clean up failed backup file
    rm -f "$BACKUP_FILE" "$BACKUP_FILE_COMPRESSED" 2>/dev/null || true
    exit 1
fi

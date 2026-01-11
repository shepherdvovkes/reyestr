#!/bin/bash
# Script to restore PostgreSQL database from backup
# Usage: ./restore_database.sh <backup_file> [--confirm]

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

# Check arguments
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: Backup file required${NC}"
    echo "Usage: $0 <backup_file> [--confirm]"
    echo ""
    echo "Available backups:"
    if [ -d "./backups" ]; then
        ls -lh ./backups/reyestr_db_backup_*.sql.gz 2>/dev/null | tail -5 || echo "No backups found"
    else
        echo "No backups directory found"
    fi
    exit 1
fi

BACKUP_FILE="$1"
CONFIRM_FLAG="$2"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

# Check if file is compressed
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo -e "${YELLOW}Backup file is compressed, will decompress during restore${NC}"
    IS_COMPRESSED=true
else
    IS_COMPRESSED=false
fi

# Set password for psql
export PGPASSWORD="$DB_PASSWORD"

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql command not found. Please install PostgreSQL client.${NC}"
    exit 1
fi

# Warning
echo -e "${RED}========================================${NC}"
echo -e "${RED}WARNING: This will REPLACE all data in the database!${NC}"
echo -e "${RED}========================================${NC}"
echo ""
echo "Database: $DB_NAME@$DB_HOST:$DB_PORT"
echo "User: $DB_USER"
echo "Backup file: $BACKUP_FILE"
echo ""

# Confirmation
if [ "$CONFIRM_FLAG" != "--confirm" ]; then
    echo -e "${YELLOW}This operation will DROP and RECREATE the database.${NC}"
    echo -e "${YELLOW}All current data will be LOST!${NC}"
    echo ""
    read -p "Type 'YES' to continue: " confirmation
    if [ "$confirmation" != "YES" ]; then
        echo -e "${YELLOW}Restore cancelled${NC}"
        exit 0
    fi
fi

echo ""
echo -e "${GREEN}Starting database restore...${NC}"

# Drop and recreate database
echo -e "${YELLOW}Dropping existing database...${NC}"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres \
    -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>&1 || true

echo -e "${YELLOW}Creating new database...${NC}"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres \
    -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>&1

# Restore from backup
echo -e "${YELLOW}Restoring from backup...${NC}"
if [ "$IS_COMPRESSED" = true ]; then
    if command -v gunzip &> /dev/null; then
        gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" 2>&1
    else
        echo -e "${RED}Error: gunzip not found. Cannot decompress backup.${NC}"
        exit 1
    fi
else
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE" 2>&1
fi

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Database restored successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # Run migrations to ensure schema is up to date
    echo ""
    echo -e "${YELLOW}Running migrations to ensure schema is up to date...${NC}"
    if [ -f "./run_migrations.sh" ]; then
        ./run_migrations.sh
    else
        echo -e "${YELLOW}Migration script not found, skipping${NC}"
    fi
    
    exit 0
else
    echo -e "${RED}✗ Restore failed${NC}"
    exit 1
fi

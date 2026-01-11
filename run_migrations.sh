#!/bin/bash
# Script to run all database migrations in order

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

# Set password for psql
export PGPASSWORD="$DB_PASSWORD"

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql command not found. Please install PostgreSQL client.${NC}"
    exit 1
fi

echo -e "${GREEN}Running database migrations...${NC}"
echo "Database: $DB_NAME@$DB_HOST:$DB_PORT"
echo "User: $DB_USER"
echo ""

# List of migrations in order
MIGRATIONS=(
    "001_add_distributed_tables.sql"
    "002_add_concurrent_connections.sql"
    "003_add_document_system_id.sql"
    "004_add_client_id_to_documents.sql"
    "005_add_document_download_progress.sql"
    "006_add_users_and_webauthn.sql"
)

MIGRATIONS_DIR="database/migrations"
SUCCESS_COUNT=0
FAILED_COUNT=0

for migration in "${MIGRATIONS[@]}"; do
    migration_path="$MIGRATIONS_DIR/$migration"
    
    if [ ! -f "$migration_path" ]; then
        echo -e "${RED}✗ Migration file not found: $migration_path${NC}"
        FAILED_COUNT=$((FAILED_COUNT + 1))
        continue
    fi
    
    echo -e "${YELLOW}Running: $migration${NC}"
    
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$migration_path" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $migration completed${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "${RED}✗ $migration failed${NC}"
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "Successful: ${GREEN}$SUCCESS_COUNT${NC}"
if [ $FAILED_COUNT -gt 0 ]; then
    echo -e "Failed: ${RED}$FAILED_COUNT${NC}"
    exit 1
else
    echo -e "${GREEN}All migrations completed successfully!${NC}"
fi

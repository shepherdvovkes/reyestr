#!/bin/bash
# Script to setup and run the download server

echo "Installing server dependencies..."

# Try to install with pip3
if command -v pip3 &> /dev/null; then
    pip3 install --user fastapi uvicorn pydantic pydantic-settings requests 2>&1 | grep -E "(Successfully|already|error|Error)" || echo "Installation completed"
else
    echo "pip3 not found. Please install Python dependencies manually:"
    echo "  pip install fastapi uvicorn pydantic pydantic-settings"
    exit 1
fi

echo ""
echo "Checking database connection..."
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='127.0.0.1',
        port=5433,
        database='reyestr_db',
        user='reyestr_user',
        password='reyestr_password'
    )
    print('✓ Database connection OK')
    conn.close()
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    exit(1)
"

echo ""
echo "Starting server..."
python3 downloader_server.py

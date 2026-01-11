#!/bin/bash
# Deployment script for Reyestr Download Server
# Usage: ./deploy.sh [start|stop|restart|logs|status]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example "$ENV_FILE"
        echo -e "${YELLOW}Please edit .env file with your configuration before deploying${NC}"
    else
        echo -e "${RED}Error: .env.example not found. Cannot create .env file.${NC}"
        exit 1
    fi
fi

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}Error: Docker is not running. Please start Docker first.${NC}"
        exit 1
    fi
}

# Function to create necessary directories
create_directories() {
    echo -e "${BLUE}Creating necessary directories...${NC}"
    mkdir -p nginx/logs nginx/ssl backups logs
    echo -e "${GREEN}✓ Directories created${NC}"
}

# Function to set PostgreSQL max_connections
setup_postgres() {
    echo -e "${BLUE}Setting up PostgreSQL...${NC}"
    # Wait for PostgreSQL to be ready
    sleep 5
    docker exec reyestr_db psql -U reyestr_user -d reyestr_db -c "ALTER SYSTEM SET max_connections = 300;" 2>/dev/null || true
    docker restart reyestr_db 2>/dev/null || true
    echo -e "${GREEN}✓ PostgreSQL configured${NC}"
}

# Function to start services
start_services() {
    check_docker
    create_directories
    
    echo -e "${BLUE}Building and starting services...${NC}"
    docker-compose -f "$COMPOSE_FILE" up -d --build
    
    echo -e "${BLUE}Waiting for services to be healthy...${NC}"
    sleep 10
    
    setup_postgres
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Services started successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "API Server: ${YELLOW}http://localhost:${NGINX_HTTP_PORT:-80}${NC}"
    echo -e "Health Check: ${YELLOW}http://localhost:${NGINX_HTTP_PORT:-80}/health${NC}"
    echo ""
    echo -e "View logs: ${BLUE}./deploy.sh logs${NC}"
    echo -e "Check status: ${BLUE}./deploy.sh status${NC}"
}

# Function to stop services
stop_services() {
    check_docker
    echo -e "${BLUE}Stopping services...${NC}"
    docker-compose -f "$COMPOSE_FILE" down
    echo -e "${GREEN}✓ Services stopped${NC}"
}

# Function to restart services
restart_services() {
    check_docker
    echo -e "${BLUE}Restarting services...${NC}"
    docker-compose -f "$COMPOSE_FILE" restart
    echo -e "${GREEN}✓ Services restarted${NC}"
}

# Function to show logs
show_logs() {
    check_docker
    docker-compose -f "$COMPOSE_FILE" logs -f
}

# Function to show status
show_status() {
    check_docker
    echo -e "${BLUE}Service Status:${NC}"
    docker-compose -f "$COMPOSE_FILE" ps
    echo ""
    echo -e "${BLUE}Container Health:${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep reyestr
}

# Function to show help
show_help() {
    echo "Reyestr Download Server Deployment Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start     - Build and start all services"
    echo "  stop      - Stop all services"
    echo "  restart   - Restart all services"
    echo "  logs      - Show logs from all services"
    echo "  status    - Show status of all services"
    echo "  help      - Show this help message"
    echo ""
}

# Main script logic
case "${1:-help}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac

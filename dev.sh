#!/bin/bash

# Auto Quran - Development Helper Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    info "Docker and Docker Compose are installed ✓"
}

# Setup environment
setup() {
    info "Setting up Auto Quran..."
    
    # Check if .env exists
    if [ ! -f "backend/.env" ]; then
        warn ".env file not found. Creating from template..."
        cp backend/.env.example backend/.env
        warn "Please edit backend/.env with your credentials before starting!"
    else
        info ".env file found ✓"
    fi
    
    # Create data directories
    mkdir -p data/assets data/output
    info "Data directories created ✓"
    
    info "Setup complete! Edit backend/.env then run: ./dev.sh start"
}

# Start services
start() {
    info "Starting Auto Quran services..."
    check_docker
    docker-compose up -d
    info "Services started ✓"
    info "Frontend: http://localhost"
    info "Backend API: http://localhost:5000/api"
    info ""
    info "View logs: ./dev.sh logs"
}

# Start in production mode
start_prod() {
    info "Starting Auto Quran in production mode..."
    check_docker
    docker-compose -f docker-compose.prod.yml up -d
    info "Production services started ✓"
}

# Stop services
stop() {
    info "Stopping Auto Quran services..."
    docker-compose down
    info "Services stopped ✓"
}

# Restart services
restart() {
    info "Restarting Auto Quran services..."
    docker-compose restart
    info "Services restarted ✓"
}

# View logs
logs() {
    docker-compose logs -f
}

# Build images
build() {
    info "Building Docker images..."
    docker-compose build
    info "Images built ✓"
}

# Clean up
clean() {
    warn "This will remove all containers and volumes. Continue? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        info "Cleaning up..."
        docker-compose down -v
        info "Cleanup complete ✓"
    else
        info "Cleanup cancelled"
    fi
}

# Show status
status() {
    info "Auto Quran Status:"
    docker-compose ps
}

# Show help
help() {
    cat << EOF
Auto Quran - Development Helper Script

Usage: ./dev.sh [command]

Commands:
    setup       - Initial setup (create .env and directories)
    start       - Start services in development mode
    start-prod  - Start services in production mode
    stop        - Stop all services
    restart     - Restart all services
    logs        - View logs (follow mode)
    build       - Build Docker images
    clean       - Remove containers and volumes
    status      - Show service status
    help        - Show this help message

Examples:
    ./dev.sh setup          # First time setup
    ./dev.sh start          # Start development
    ./dev.sh logs           # View logs
    ./dev.sh stop           # Stop services

EOF
}

# Main script
case "${1:-help}" in
    setup)
        setup
        ;;
    start)
        start
        ;;
    start-prod)
        start_prod
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs
        ;;
    build)
        build
        ;;
    clean)
        clean
        ;;
    status)
        status
        ;;
    help|*)
        help
        ;;
esac

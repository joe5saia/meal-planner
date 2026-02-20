#!/bin/bash

# Meal Planner - Development Server Runner
# Usage: ./run.sh [setup|start|backend|frontend]

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[Meal Planner]${NC} $1"
}

setup_backend() {
    log "Setting up backend..."
    cd "$BACKEND_DIR"

    if ! command -v uv >/dev/null 2>&1; then
        echo "Error: uv is required for backend setup. Install from https://docs.astral.sh/uv/"
        exit 1
    fi

    if [ ! -d ".venv" ]; then
        log "Creating Python virtual environment with uv..."
        uv venv
    fi

    log "Installing backend dependencies with uv..."
    uv sync --group dev

    log "Backend setup complete!"
}

setup_frontend() {
    log "Setting up frontend..."
    cd "$FRONTEND_DIR"
    
    if [ ! -d "node_modules" ]; then
        log "Installing Node dependencies..."
        npm install
    fi
    
    log "Frontend setup complete!"
}

start_backend() {
    cd "$BACKEND_DIR"
    log "Starting backend on http://localhost:8000"
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

start_frontend() {
    cd "$FRONTEND_DIR"
    log "Starting frontend on http://localhost:5173"
    npm run dev
}

case "${1:-start}" in
    setup)
        setup_backend
        setup_frontend
        log "Setup complete! Run './run.sh' to start the app."
        ;;
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    start|"")
        # Check if setup is needed
        if [ ! -d "$BACKEND_DIR/.venv" ] || [ ! -d "$FRONTEND_DIR/node_modules" ]; then
            log "First run detected. Running setup..."
            setup_backend
            setup_frontend
        fi
        
        log "Starting Meal Planner..."
        echo ""
        echo -e "${BLUE}Backend:${NC}  http://localhost:8000"
        echo -e "${BLUE}Frontend:${NC} http://localhost:5173"
        echo -e "${BLUE}API Docs:${NC} http://localhost:8000/docs"
        echo ""
        log "Press Ctrl+C to stop both servers"
        echo ""
        
        # Start both servers
        cd "$BACKEND_DIR"
        uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
        BACKEND_PID=$!
        
        cd "$FRONTEND_DIR"
        npm run dev &
        FRONTEND_PID=$!
        
        # Handle Ctrl+C
        trap "log 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
        
        # Wait for either to exit
        wait
        ;;
    *)
        echo "Usage: $0 [setup|start|backend|frontend]"
        echo ""
        echo "Commands:"
        echo "  setup     - Install all dependencies"
        echo "  start     - Start both backend and frontend (default)"
        echo "  backend   - Start only the backend"
        echo "  frontend  - Start only the frontend"
        exit 1
        ;;
esac

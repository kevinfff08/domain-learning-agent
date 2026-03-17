#!/usr/bin/env bash
# ============================================================
# NewLearner - One-click startup script (Linux / macOS / WSL)
# ============================================================
# Starts: backend API + frontend dev server
# Optional: CLIProxyAPI proxy (if LLM_MODE=setup-token in .env)
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- Check .env ---
if [ ! -f ".env" ]; then
    echo -e "${RED}[ERROR]${NC} .env file not found. Creating from .env.example ..."
    cp .env.example .env
    echo -e "${YELLOW}[INFO]${NC} Please edit .env to configure your settings, then re-run this script."
    exit 1
fi

# --- Read LLM_MODE from .env ---
LLM_MODE=$(grep -E '^LLM_MODE=' .env | cut -d'=' -f2 | tr -d ' \r' || echo "api-key")
LLM_MODE=${LLM_MODE:-api-key}

echo "============================================================"
echo " NewLearner - Starting services"
echo " LLM Mode: $LLM_MODE"
echo "============================================================"

# Track PIDs for cleanup
PIDS=()

cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# --- Start CLIProxyAPI if setup-token mode ---
if [ "$LLM_MODE" = "setup-token" ]; then
    echo ""
    echo "[1/3] Starting CLIProxyAPI proxy on localhost:8317 ..."
    if ! command -v cliproxyapi &>/dev/null; then
        echo -e "${RED}[ERROR]${NC} cliproxyapi not found. Install it first:"
        echo "        brew install router-for-me/tap/cliproxyapi  (macOS)"
        echo "        curl -fsSL https://raw.githubusercontent.com/router-for-me/CLIProxyAPI/main/install.sh | bash  (Linux)"
        exit 1
    fi
    cliproxyapi &
    PIDS+=($!)
    sleep 2
    echo -e "${GREEN}[OK]${NC} CLIProxyAPI proxy started (PID: ${PIDS[-1]})"
else
    echo ""
    echo "[1/3] Skipping proxy (api-key mode)"
fi

# --- Start backend ---
echo ""
echo "[2/3] Starting FastAPI backend on localhost:8000 ..."
python -m src.api.app &
PIDS+=($!)
sleep 2
echo -e "${GREEN}[OK]${NC} Backend started (PID: ${PIDS[-1]})"

# --- Start frontend ---
echo ""
echo "[3/3] Starting React frontend on localhost:5173 ..."
(cd frontend && npm run dev) &
PIDS+=($!)
sleep 2
echo -e "${GREEN}[OK]${NC} Frontend started (PID: ${PIDS[-1]})"

echo ""
echo "============================================================"
echo " All services running!"
echo " Open: http://localhost:5173"
echo ""
echo " Press Ctrl+C to stop all services."
echo "============================================================"

# Wait for all background processes
wait

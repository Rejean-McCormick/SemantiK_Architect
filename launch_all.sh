#!/bin/bash
# launch_all.sh

# ==============================================================================
# 🚀 Abstract Wiki Architect v2.0 - Unified Launch Script
# ==============================================================================
# Usage: ./launch_all.sh
# Purpose: Automates the startup of Redis, Build System, API, and Worker.
# ==============================================================================

# 1. ENVIRONMENT SETUP
# --------------------
PROJECT_ROOT="/mnt/c/MyCode/AbstractWiki/abstract-wiki-architect"
VENV_ACTIVATE="$PROJECT_ROOT/venv/bin/activate"

echo "[*] Setting up environment..."
cd "$PROJECT_ROOT" || { echo "❌ Failed to cd to $PROJECT_ROOT"; exit 1; }

# Activate Python Virtual Env
if [ -f "$VENV_ACTIVATE" ]; then
    source "$VENV_ACTIVATE"
else
    echo "❌ Virtualenv not found at $VENV_ACTIVATE. Run 'python3 -m venv venv' first."
    exit 1
fi

# 2. STATE STORE CHECK (Redis)
# ----------------------------
echo "[*] Checking Redis..."
if [ "$(docker ps -q -f name=aw_redis)" ]; then
    echo "✅ Redis is already running."
else
    if [ "$(docker ps -aq -f status=exited -f name=aw_redis)" ]; then
        # Cleanup old stopped container
        docker rm aw_redis > /dev/null
    fi
    echo "🚀 Starting Redis container..."
    docker run -p 6379:6379 --name aw_redis -d redis:alpine > /dev/null
    # Wait for Redis to be ready
    sleep 2
fi

# 3. BUILD PIPELINE (Audit & Compile)
# -----------------------------------
echo "[*] Running System Audit (The Matrix)..."
python tools/everything_matrix/build_index.py

echo "[*] Compiling Grammar Engine (Two-Phase Build)..."
cd gf || exit
python build_orchestrator.py
BUILD_STATUS=$?
cd ..

if [ $BUILD_STATUS -ne 0 ]; then
    echo "❌ Build failed. Aborting launch."
    exit 1
fi

# 4. LAUNCH SERVICES
# ------------------
# We use 'trap' to kill background processes when you hit Ctrl+C
trap 'kill $(jobs -p)' EXIT

echo "[*] Launching API Backend (Port 8000)..."
uvicorn app.adapters.api.main:create_app --factory --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

echo "[*] Launching Async Worker..."
arq app.workers.worker.WorkerSettings --watch app &
WORKER_PID=$!

# 5. KEEP ALIVE
# -------------
echo "✅ SYSTEM LIVE!"
echo "   - API: http://localhost:8000/docs"
echo "   - Redis: localhost:6379"
echo "   - Worker: Active"
echo "PRESS CTRL+C TO STOP ALL SERVICES"

wait
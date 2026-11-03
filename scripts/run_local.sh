#!/usr/bin/env bash
# Shell script to start Finance Tracker Pro locally on Linux/macOS
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=========================================================="
echo "   Finance Tracker Pro - Local Development Launcher      "
echo "=========================================================="

echo -e "\n[1/3] Running migrations..."
cd "$ROOT_DIR/backend"
python manage.py migrate

echo -e "\n[2/3] Starting Flask ML microservice (port 5001)..."
python "$ROOT_DIR/ml_service/app.py" &
ML_PID=$!

trap "kill $ML_PID 2>/dev/null || true" EXIT

echo -e "\n[3/3] Starting Django server on http://127.0.0.1:8000..."
echo "Demo Login: demo_user / Demo@123456"
python manage.py runserver 0.0.0.0:8000


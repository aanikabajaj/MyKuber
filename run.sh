#!/usr/bin/env bash
# IAARE one-shot launcher (macOS / Linux)
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Setting up IAARE backend..."
cd "$ROOT/backend"
[ -d .venv ] || python3 -m venv .venv
./.venv/bin/pip install --upgrade pip >/dev/null
./.venv/bin/pip install -r requirements.txt >/dev/null

echo "==> Launching backend on http://localhost:8000"
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "==> Setting up IAARE frontend..."
cd "$ROOT/frontend"
[ -d node_modules ] || npm install --no-audit --no-fund

echo "==> Launching frontend on http://localhost:5173"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "IAARE running:"
echo "  Frontend : http://localhost:5173"
echo "  Backend  : http://localhost:8000  (docs at /docs)"
echo ""
echo "── Mobile App (Expo) ──────────────────────────────────────────────────"
echo "  To run the mobile app:"
echo "    1. Find your LAN IP: ifconfig (Mac) / ip addr (Linux)"
echo "    2. Edit mobile/.env  →  EXPO_PUBLIC_API_URL=http://<LAN_IP>:8000"
echo "    3. In a new terminal:"
echo "         cd mobile"
echo "         npx expo start"
echo "    4. Scan the QR code with the Expo Go app on your phone"
echo "   (Expo web preview runs on http://localhost:8081)"
echo ""
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait

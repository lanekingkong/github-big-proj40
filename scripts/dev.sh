#!/bin/bash
set -e

echo "Starting AgentForge development environment..."
echo ""

# Start backend in background
echo "Starting Python backend..."
cd backend && python main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
cd ..
echo "Starting Electron + React dev server..."
npm run dev

# Cleanup
kill $BACKEND_PID 2>/dev/null

#!/bin/bash
set -e

echo "============================================"
echo "  AgentForge - Linux/macOS Installer"
echo "============================================"
echo ""

echo "[1/3] Installing Node.js dependencies..."
npm install

echo "[2/3] Installing Python dependencies..."
pip install -r requirements.txt

echo "[3/3] Creating environment file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi

echo ""
echo "============================================"
echo "  Installation complete!"
echo "  Run: npm run dev"
echo "============================================"

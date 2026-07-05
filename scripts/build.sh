#!/bin/bash
set -e

echo "Building AgentForge for production..."
echo ""

echo "Building Electron app..."
npm run electron:build

echo ""
echo "============================================"
echo "  Build complete!"
echo "  Output: dist/"
echo "============================================"

#!/usr/bin/env bash
set -euo pipefail

# macOS build script for Roaster Logger
# Requires pyinstaller installed in the active environment.

pyinstaller --windowed --onefile \
  --name RoasterLogger \
  --icon icon.icns \
  --add-data "config:config" \
  --add-data "data:data" \
  ui/desktop/app.py

echo "Build finished. Output is under dist/RoasterLogger.app"

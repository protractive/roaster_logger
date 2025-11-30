#!/usr/bin/env bash
set -euo pipefail

# Linux build script for Roaster Logger
# Requires pyinstaller installed in the active environment.

pyinstaller --windowed --onefile \
  --name roaster_logger \
  --icon icon.png \
  --add-data "config:config" \
  --add-data "data:data" \
  ui/desktop/app.py

echo "Build finished. Output is under dist/roaster_logger"

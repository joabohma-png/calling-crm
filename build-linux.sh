#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
python3 -m PyInstaller --noconfirm --clean --onedir --name CallingCRM --paths . launcher.py
mkdir -p dist/CallingCRM/data
cp start-linux.sh dist/CallingCRM/start-linux.sh
echo "Byggd: dist/CallingCRM"

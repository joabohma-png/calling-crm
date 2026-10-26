#!/usr/bin/env bash
set -euo pipefail
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"
exec python3 -m calling_crm --db "$BASE_DIR/data/calling_crm.sqlite3"

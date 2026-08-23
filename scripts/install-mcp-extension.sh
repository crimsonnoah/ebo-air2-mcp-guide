#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="${1:-/opt/ha-enabot}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TARGET="$SOURCE_DIR/ebo/ebo_mcp.py"

if [[ ! -f "$TARGET" || ! -f "$SOURCE_DIR/docker-compose.yml" ]]; then
  echo "Expected a ha-enabot checkout at: $SOURCE_DIR" >&2
  exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
cp -- "$TARGET" "$TARGET.backup-$STAMP"
install -m 0644 "$REPO_DIR/patches/ebo_mcp.py" "$TARGET"

python3 -m py_compile "$TARGET"
echo "Installed extended ebo_mcp.py; backup: $TARGET.backup-$STAMP"
if ! grep -Eq '^[[:space:]]*build:[[:space:]]*\./ebo' "$SOURCE_DIR/docker-compose.yml"; then
  echo "WARNING: docker-compose.yml is still using only the published image." >&2
  echo "Enable 'build: ./ebo' and disable the 'image:' line, or Docker will ignore this local patch." >&2
fi
echo "Next: cd '$SOURCE_DIR' && docker compose up -d --build ebo-engine"

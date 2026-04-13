#!/usr/bin/env bash
set -euo pipefail

PORT="8001"
MIGRATE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--port)
      PORT="$2"; shift 2 ;;
    --migrate)
      MIGRATE="true"; shift ;;
    *)
      echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "Missing command: uv" >&2
  exit 1
fi

if [[ "$MIGRATE" == "true" ]]; then
  uv run python ./django_registry/manage.py migrate
fi

echo "[start] Metadata Registry Service -> 0.0.0.0:$PORT"
uv run python ./django_registry/manage.py runserver 0.0.0.0:"$PORT"

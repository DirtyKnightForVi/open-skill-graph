#!/usr/bin/env bash
set -euo pipefail

MODE="all"
KEEP_REDIS="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--mode)
      MODE="$2"; shift 2 ;;
    --keep-redis)
      KEEP_REDIS="true"; shift ;;
    *)
      echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ ! "$MODE" =~ ^(all|minimal|registry|redis|full)$ ]]; then
  echo "Invalid mode: $MODE" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

RUN_DIR="$REPO_ROOT/.run"

stop_by_pid_file() {
  local name="$1"
  local pid_file="$2"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid=$(cat "$pid_file" || true)
    if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
      echo "[stop] $name (pid=$pid)"
    fi
    rm -f "$pid_file"
  fi
}

STOP_MAIN="true"
STOP_SANDBOX="true"
STOP_REGISTRY="false"
STOP_REDIS="false"

case "$MODE" in
  all|full)
    STOP_REGISTRY="true"
    STOP_REDIS="true"
    ;;
  registry)
    STOP_REGISTRY="true"
    ;;
  redis)
    STOP_REDIS="true"
    ;;
  minimal)
    ;;
esac

if [[ "$KEEP_REDIS" == "true" ]]; then
  STOP_REDIS="false"
fi

[[ "$STOP_MAIN" == "true" ]] && stop_by_pid_file "main" "$RUN_DIR/main.pid"
[[ "$STOP_SANDBOX" == "true" ]] && stop_by_pid_file "sandbox" "$RUN_DIR/sandbox.pid"
[[ "$STOP_REGISTRY" == "true" ]] && stop_by_pid_file "metadata-registry" "$RUN_DIR/metadata-registry.pid"

if [[ "$STOP_REDIS" == "true" && -f "$RUN_DIR/services.state.json" ]]; then
  if command -v docker >/dev/null 2>&1; then
    name=$(python - <<'PY' "$RUN_DIR/services.state.json"
import json
import sys
try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(data.get('redis_container', ''))
except Exception:
    print('')
PY
)
    if [[ -n "$name" ]] && docker ps -a --format '{{.Names}}' | grep -Fx "$name" >/dev/null 2>&1; then
      docker stop "$name" >/dev/null
      echo "[stop] redis container $name"
    fi
  fi
fi

echo "[done] stop script completed (mode=$MODE)"

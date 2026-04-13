#!/usr/bin/env bash
set -euo pipefail

MODE="minimal"
ENV_FILE=".env"
SANDBOX_ENV_FILE="sandbox.env"
HEALTH_ONLY="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--mode)
      MODE="$2"; shift 2 ;;
    --env-file)
      ENV_FILE="$2"; shift 2 ;;
    --sandbox-env-file)
      SANDBOX_ENV_FILE="$2"; shift 2 ;;
    --health-only)
      HEALTH_ONLY="true"; shift ;;
    *)
      echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ ! "$MODE" =~ ^(minimal|registry|redis|full)$ ]]; then
  echo "Invalid mode: $MODE" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

RUN_DIR="$REPO_ROOT/.run"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

assert_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing command: $1" >&2
    exit 1
  fi
}

read_env_value() {
  local file="$1"
  local key="$2"
  local default_value="$3"
  if [[ ! -f "$file" ]]; then
    printf "%s" "$default_value"
    return
  fi

  local line
  line=$(grep -E "^[[:space:]]*$key=" "$file" | tail -n 1 || true)
  if [[ -z "$line" ]]; then
    printf "%s" "$default_value"
    return
  fi

  local value="${line#*=}"
  value="${value%\"}"
  value="${value#\"}"
  value="${value%\'}"
  value="${value#\'}"
  printf "%s" "$value"
}

parse_url_host() {
  local url="$1"
  local default_host="$2"
  local host
  host=$(printf "%s" "$url" | sed -E 's#^[a-zA-Z]+://##' | sed -E 's#/.*$##' | sed -E 's/:.*$//')
  if [[ -z "$host" ]]; then
    host="$default_host"
  fi
  printf "%s" "$host"
}

parse_url_port() {
  local url="$1"
  local default_port="$2"
  local port
  port=$(printf "%s" "$url" | sed -nE 's#^[a-zA-Z]+://[^/:]+:([0-9]+).*$#\1#p')
  if [[ -z "$port" ]]; then
    port="$default_port"
  fi
  printf "%s" "$port"
}

test_tcp_port() {
  local host="$1"
  local port="$2"
  python - <<'PY' "$host" "$port"
import socket
import sys
host = sys.argv[1]
port = int(sys.argv[2])
s = socket.socket()
s.settimeout(0.8)
try:
    s.connect((host, port))
except OSError:
    sys.exit(1)
finally:
    s.close()
PY
}

wait_port_ready() {
  local name="$1"
  local host="$2"
  local port="$3"
  local retry="${4:-40}"

  for ((i=0; i<retry; i++)); do
    if test_tcp_port "$host" "$port"; then
      echo "[ok] $name is ready at $host:$port"
      return 0
    fi
    sleep 1
  done
  return 1
}

start_service_shell() {
  local name="$1"
  local command="$2"
  local log_path="$LOG_DIR/$name.log"
  local pid_path="$RUN_DIR/$name.pid"

  nohup bash -lc "cd '$REPO_ROOT'; $command" >> "$log_path" 2>&1 &
  local pid=$!
  printf "%s" "$pid" > "$pid_path"
  echo "[start] $name started (pid=$pid, log=$log_path)"
}

is_local_host() {
  local host="${1,,}"
  [[ "$host" == "127.0.0.1" || "$host" == "localhost" || "$host" == "::1" || "$host" == "0.0.0.0" ]]
}

check_and_report() {
  local name="$1"
  local host="$2"
  local port="$3"
  local required="$4"
  local status="FAILED"
  if test_tcp_port "$host" "$port"; then
    status="OK"
  fi
  echo "[check] $name $host:$port [$required] -> $status"
  [[ "$status" == "OK" ]]
}

assert_command uv

SANDBOX_SERVICE_URL=$(read_env_value "$ENV_FILE" "SANDBOX_SERVICE_URL" "http://127.0.0.1:8000")
SESSION_TYPE=$(read_env_value "$ENV_FILE" "SESSION_TYPE" "json")
REDIS_HOST=$(read_env_value "$ENV_FILE" "REDIS_HOST" "127.0.0.1")
REDIS_PORT=$(read_env_value "$ENV_FILE" "REDIS_PORT" "6379")
SKILL_METADATA_SOURCE=$(read_env_value "$ENV_FILE" "SKILL_METADATA_SOURCE" "meta")
REGISTRY_BASE_URL=$(read_env_value "$ENV_FILE" "REGISTRY_BASE_URL" "http://127.0.0.1:8001")

SANDBOX_HOST=$(parse_url_host "$SANDBOX_SERVICE_URL" "127.0.0.1")
SANDBOX_PORT=$(parse_url_port "$SANDBOX_SERVICE_URL" "8000")
REGISTRY_HOST=$(parse_url_host "$REGISTRY_BASE_URL" "127.0.0.1")
REGISTRY_PORT=$(parse_url_port "$REGISTRY_BASE_URL" "8001")
MAIN_HOST="127.0.0.1"
MAIN_PORT="3000"

NEED_REGISTRY="false"
NEED_REDIS="false"
[[ "$MODE" == "registry" || "$MODE" == "full" ]] && NEED_REGISTRY="true"
[[ "$MODE" == "redis" || "$MODE" == "full" ]] && NEED_REDIS="true"

echo "[mode] $MODE"
echo "[config] sandbox=$SANDBOX_HOST:$SANDBOX_PORT, registry=$REGISTRY_HOST:$REGISTRY_PORT, redis=$REDIS_HOST:$REDIS_PORT"

if [[ "${SKILL_METADATA_SOURCE,,}" == "registry" && "$NEED_REGISTRY" != "true" ]]; then
  echo "[warn] .env uses SKILL_METADATA_SOURCE=registry, but mode=$MODE does not start registry"
fi
if [[ "${SESSION_TYPE,,}" == "redis" && "$NEED_REDIS" != "true" ]]; then
  echo "[warn] .env uses SESSION_TYPE=redis, but mode=$MODE does not start redis"
fi

FAILED_REQUIRED=()
check_and_report "sandbox" "$SANDBOX_HOST" "$SANDBOX_PORT" "required" || FAILED_REQUIRED+=("sandbox($SANDBOX_HOST:$SANDBOX_PORT)")
check_and_report "main" "$MAIN_HOST" "$MAIN_PORT" "optional" || true
if [[ "$NEED_REGISTRY" == "true" ]]; then
  check_and_report "metadata-registry" "$REGISTRY_HOST" "$REGISTRY_PORT" "required" || FAILED_REQUIRED+=("metadata-registry($REGISTRY_HOST:$REGISTRY_PORT)")
fi
if [[ "$NEED_REDIS" == "true" ]]; then
  check_and_report "redis" "$REDIS_HOST" "$REDIS_PORT" "required" || FAILED_REQUIRED+=("redis($REDIS_HOST:$REDIS_PORT)")
fi

if [[ "$HEALTH_ONLY" == "true" ]]; then
  if [[ ${#FAILED_REQUIRED[@]} -gt 0 ]]; then
    echo "Health check failed. Missing required services: ${FAILED_REQUIRED[*]}" >&2
    exit 1
  fi
  echo "[done] health-only check passed"
  exit 0
fi

if ! test_tcp_port "$SANDBOX_HOST" "$SANDBOX_PORT"; then
  start_service_shell "sandbox" "uv run --env-file '$SANDBOX_ENV_FILE' ./sandbox_service.py"
  wait_port_ready "sandbox" "$SANDBOX_HOST" "$SANDBOX_PORT" || { echo "Sandbox not ready at $SANDBOX_HOST:$SANDBOX_PORT" >&2; exit 1; }
else
  echo "[skip] sandbox already running at $SANDBOX_HOST:$SANDBOX_PORT"
fi

if [[ "$NEED_REGISTRY" == "true" ]]; then
  if ! test_tcp_port "$REGISTRY_HOST" "$REGISTRY_PORT"; then
    start_service_shell "metadata-registry" "uv run python ./django_registry/manage.py migrate; uv run python ./django_registry/manage.py runserver 0.0.0.0:$REGISTRY_PORT"
    wait_port_ready "metadata-registry" "$REGISTRY_HOST" "$REGISTRY_PORT" || { echo "Metadata registry not ready at $REGISTRY_HOST:$REGISTRY_PORT" >&2; exit 1; }
  else
    echo "[skip] metadata-registry already running at $REGISTRY_HOST:$REGISTRY_PORT"
  fi
fi

REDIS_CONTAINER="open-skill-graph-redis"
if [[ "$NEED_REDIS" == "true" ]]; then
  if is_local_host "$REDIS_HOST"; then
    if ! test_tcp_port "$REDIS_HOST" "$REDIS_PORT"; then
      assert_command docker
      if docker ps -a --format '{{.Names}}' | grep -Fx "$REDIS_CONTAINER" >/dev/null 2>&1; then
        docker start "$REDIS_CONTAINER" >/dev/null
        echo "[start] redis container restarted: $REDIS_CONTAINER"
      else
        docker run -d --name "$REDIS_CONTAINER" -p "$REDIS_PORT:6379" redis:7-alpine >/dev/null
        echo "[start] redis container created: $REDIS_CONTAINER (host port $REDIS_PORT)"
      fi
      wait_port_ready "redis" "$REDIS_HOST" "$REDIS_PORT" || { echo "Redis not ready at $REDIS_HOST:$REDIS_PORT" >&2; exit 1; }
    else
      echo "[skip] redis already running at $REDIS_HOST:$REDIS_PORT"
    fi
  else
    test_tcp_port "$REDIS_HOST" "$REDIS_PORT" || { echo "Remote redis unreachable: $REDIS_HOST:$REDIS_PORT" >&2; exit 1; }
    echo "[ok] remote redis reachable at $REDIS_HOST:$REDIS_PORT"
  fi
fi

if ! test_tcp_port "$MAIN_HOST" "$MAIN_PORT"; then
  start_service_shell "main" "uv run python ./main.py"
  wait_port_ready "main" "$MAIN_HOST" "$MAIN_PORT" || { echo "Main service not ready at $MAIN_HOST:$MAIN_PORT" >&2; exit 1; }
else
  echo "[skip] main already running at $MAIN_HOST:$MAIN_PORT"
fi

REDIS_CONTAINER_VALUE=""
if [[ "$NEED_REDIS" == "true" ]] && is_local_host "$REDIS_HOST"; then
  REDIS_CONTAINER_VALUE="$REDIS_CONTAINER"
fi

cat > "$RUN_DIR/services.state.json" <<JSON
{
  "started_at": "$(date +%Y-%m-%dT%H:%M:%S)",
  "mode": "$MODE",
  "env_file": "$ENV_FILE",
  "sandbox": "$SANDBOX_HOST:$SANDBOX_PORT",
  "metadata_registry": "$REGISTRY_HOST:$REGISTRY_PORT",
  "redis": "$REDIS_HOST:$REDIS_PORT",
  "redis_container": "$REDIS_CONTAINER_VALUE",
  "main": "$MAIN_HOST:$MAIN_PORT"
}
JSON

echo "[done] startup finished. main=http://$MAIN_HOST:$MAIN_PORT"

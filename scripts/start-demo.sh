#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${INF3_DATA_ROOT:=$ROOT_DIR/demo_data}"
: "${INF3_REGISTRY_PATH:=$INF3_DATA_ROOT/registry.json}"
: "${INF3_MAX_UPLOAD_SIZE_MB:=300}"
: "${NEXT_PUBLIC_INF3_API_BASE:=/api}"
: "${BASIC_AUTH_USER:=tester}"
: "${INF3_API_PORT:=8001}"
: "${INF3_FRONTEND_PORT:=3000}"
: "${INF3_CADDY_PORT:=8080}"
: "${NO_TUNNEL:=0}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

require_port_free() {
  local port="$1"
  local name="$2"
  if ss -ltn "sport = :${port}" 2>/dev/null | grep -q ":${port}"; then
    echo "Port ${port} (${name}) is already in use."
    echo "Run scripts/stop-demo.sh first, or kill the process: sudo ss -lptn 'sport = :${port}'"
    exit 1
  fi
}

wait_for_port() {
  local port="$1"
  local name="$2"
  local log="$3"
  local i
  for i in {1..30}; do
    if ss -ltn "sport = :${port}" 2>/dev/null | grep -q ":${port}"; then
      return 0
    fi
    sleep 0.5
  done
  echo "${name} did not start on port ${port}."
  if [[ -f "$log" ]]; then
    echo "Last 50 lines of ${log}:"
    tail -n 50 "$log"
  fi
  exit 1
}

require_cmd uv
require_cmd npm
require_cmd caddy
if [[ "$NO_TUNNEL" != "1" ]]; then
  require_cmd cloudflared
fi

require_port_free "$INF3_API_PORT" "API"
require_port_free "$INF3_FRONTEND_PORT" "Frontend"
require_port_free "$INF3_CADDY_PORT" "Caddy"

if [[ -n "${BASIC_AUTH_PASS:-}" ]]; then
  BASIC_AUTH_HASH="$(caddy hash-password --plaintext "${BASIC_AUTH_PASS}")"
  export BASIC_AUTH_HASH
elif [[ -z "${BASIC_AUTH_HASH:-}" ]]; then
  echo "Missing BASIC_AUTH_PASS or BASIC_AUTH_HASH."
  echo "Set BASIC_AUTH_PASS to a plaintext password, or BASIC_AUTH_HASH to a caddy hash."
  exit 1
fi

case "$BASIC_AUTH_HASH" in
  \$2a\$*|\$2b\$*|\$2y\$*) ;;
  *)
    echo "BASIC_AUTH_HASH does not look like a bcrypt hash."
    echo "Unset BASIC_AUTH_HASH and set BASIC_AUTH_PASS instead."
    exit 1
    ;;
esac

mkdir -p "$INF3_DATA_ROOT/logs"

# Generate Caddyfile with configured ports
# flush_interval -1 disables response buffering on the API proxy, required for SSE streams
CADDYFILE="$INF3_DATA_ROOT/logs/Caddyfile"
cat >"$CADDYFILE" <<CADDYEOF
{
  admin off
}

:${INF3_CADDY_PORT} {
  basicauth {
    ${BASIC_AUTH_USER} ${BASIC_AUTH_HASH}
  }

  handle_path /api* {
    reverse_proxy 127.0.0.1:${INF3_API_PORT} {
      flush_interval -1
    }
  }

  handle {
    reverse_proxy 127.0.0.1:${INF3_FRONTEND_PORT}
  }
}
CADDYEOF

cleanup() {
  echo "Stopping demo processes..."
  [[ -n "${API_PID:-}" ]] && kill "$API_PID" >/dev/null 2>&1 || true
  [[ -n "${FRONTEND_PID:-}" ]] && kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  [[ -n "${CADDY_PID:-}" ]] && kill "$CADDY_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

echo "Starting API..."
(
  cd "$ROOT_DIR"
  INF3_DATA_ROOT="$INF3_DATA_ROOT" \
  INF3_REGISTRY_PATH="$INF3_REGISTRY_PATH" \
  INF3_MAX_UPLOAD_SIZE_MB="$INF3_MAX_UPLOAD_SIZE_MB" \
  uv run --extra cloud --extra api uvicorn inf3_analytics.api.app:app --host 127.0.0.1 --port "$INF3_API_PORT"
) >"$INF3_DATA_ROOT/logs/api.log" 2>&1 &
API_PID=$!
wait_for_port "$INF3_API_PORT" "API" "$INF3_DATA_ROOT/logs/api.log"

echo "Starting frontend..."
(
  cd "$ROOT_DIR/frontend"
  NEXT_PUBLIC_INF3_API_BASE="$NEXT_PUBLIC_INF3_API_BASE" \
  npm run dev -- --hostname 127.0.0.1 --port "$INF3_FRONTEND_PORT"
) >"$INF3_DATA_ROOT/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
wait_for_port "$INF3_FRONTEND_PORT" "Frontend" "$INF3_DATA_ROOT/logs/frontend.log"

echo "Starting Caddy..."
(
  cd "$ROOT_DIR"
  caddy run --config "$CADDYFILE"
) >"$INF3_DATA_ROOT/logs/caddy.log" 2>&1 &
CADDY_PID=$!
wait_for_port "$INF3_CADDY_PORT" "Caddy" "$INF3_DATA_ROOT/logs/caddy.log"

if [[ "$NO_TUNNEL" == "1" ]]; then
  echo ""
  echo "Demo running locally (no tunnel)."
  echo "  http://localhost:${INF3_CADDY_PORT}  (basic auth: ${BASIC_AUTH_USER} / <your password>)"
  echo ""
  echo "Press Ctrl+C to stop everything."
  # Keep running until interrupted
  while true; do sleep 60; done
else
  echo "Starting Cloudflare quick tunnel..."
  echo "Press Ctrl+C to stop everything."
  cloudflared tunnel --url "http://127.0.0.1:${INF3_CADDY_PORT}"
fi

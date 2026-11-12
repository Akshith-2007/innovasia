#!/usr/bin/env bash
# Kisan Cold Link — start FastAPI + Vite together. Ctrl+C stops both.
# Does NOT: start a database, start Docker, download datasets, train models or create sample records.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
API_HOST="${API_HOST:-127.0.0.1}"   # API_HOST=0.0.0.0 lets the ESP32 reach the API over Wi-Fi
API_PORT="${API_PORT:-8000}"   # override if 8000 is taken: API_PORT=8010 ./dev.sh
WEB_PORT=5173

say() { printf '\033[1;32m[dev]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[dev]\033[0m %s\n' "$*" >&2; exit 1; }

# --- dependency checks ----------------------------------------------------------------------
PY=""
for c in python3 python py; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
[ -n "$PY" ] || die "Python 3.11+ is required."
command -v node >/dev/null 2>&1 || die "Node.js 20+ is required."
command -v npm >/dev/null 2>&1 || die "npm is required."

# --- backend environment --------------------------------------------------------------------
if [ ! -d "$BACKEND/.venv" ]; then
  say "Creating Python virtual environment"
  "$PY" -m venv "$BACKEND/.venv"
fi
if [ -x "$BACKEND/.venv/Scripts/python.exe" ]; then
  VPY="$BACKEND/.venv/Scripts/python.exe"   # Windows (Git Bash)
else
  VPY="$BACKEND/.venv/bin/python"
fi
STAMP="$BACKEND/.venv/.requirements.sha"
REQ_SHA="$("$VPY" -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$BACKEND/requirements.txt")"
if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$REQ_SHA" ]; then
  say "Installing backend dependencies"
  "$VPY" -m pip install -q --upgrade pip
  "$VPY" -m pip install -q -r "$BACKEND/requirements.txt"
  echo "$REQ_SHA" > "$STAMP"
fi
[ -f "$BACKEND/.env" ] || say "backend/.env not found — live data.gov.in calls disabled (copy backend/.env.example)."

# --- frontend packages ----------------------------------------------------------------------
if [ ! -d "$FRONTEND/node_modules" ] || [ "$FRONTEND/package.json" -nt "$FRONTEND/node_modules" ]; then
  say "Installing frontend packages"
  (cd "$FRONTEND" && npm install --no-audit --no-fund)
  touch "$FRONTEND/node_modules"
fi

# --- run --------------------------------------------------------------------------------------
port_busy() {
  "$VPY" -c "import socket,sys; s=socket.socket(); s.settimeout(0.5); sys.exit(0 if s.connect_ex(('127.0.0.1', int(sys.argv[1])))==0 else 1)" "$1"
}
for port in "$API_PORT" "$WEB_PORT"; do
  port_busy "$port" && die "Port $port is already in use. Stop that program, or for the API choose another port: API_PORT=8010 ./dev.sh"
done

PIDS=()
WINPIDS=()
cleanup() {
  trap - INT TERM EXIT
  say "Stopping services"
  # Windows (Git Bash): kill each native process tree first, while its Windows PID is still known.
  if command -v taskkill >/dev/null 2>&1; then
    for wp in "${WINPIDS[@]:-}"; do
      [ -n "$wp" ] && taskkill //F //T //PID "$wp" >/dev/null 2>&1 || true
    done
  fi
  for pid in "${PIDS[@]:-}"; do
    [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
  done
  # Windows: Git Bash exec can re-spawn processes, so recorded PIDs may miss children. Both ports were
  # verified free at start, so whatever listens on them now is ours: stop those process trees too.
  if command -v taskkill >/dev/null 2>&1; then
    for port in "$API_PORT" "$WEB_PORT"; do
      for wp in $(netstat -ano 2>/dev/null | awk -v p=":$port" '$4 == "LISTENING" && substr($2, length($2) - length(p) + 1) == p {print $5}' | sort -u); do
        taskkill //F //T //PID "$wp" >/dev/null 2>&1 || true
      done
    done
  fi
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

start() {  # start <dir> <command...> ; records POSIX and Windows PIDs
  local dir="$1"; shift
  (cd "$dir" && exec "$@") &
  PIDS+=($!)
  if [ -r "/proc/$!/winpid" ]; then WINPIDS+=("$(cat "/proc/$!/winpid")"); fi
}

start "$BACKEND" "$VPY" -m uvicorn app.main:app --host "$API_HOST" --port "$API_PORT" --reload
export VITE_API_BASE_URL="http://127.0.0.1:$API_PORT/api/v1"
start "$FRONTEND" npm run dev

say "Website   http://127.0.0.1:$WEB_PORT"
say "API       http://$API_HOST:$API_PORT"
[ "$API_HOST" = "0.0.0.0" ] && say "ESP32 URL http://<this laptop Wi-Fi IP>:$API_PORT/api/v1  (allow Python through Windows Firewall)"
say "API docs  http://$API_HOST:$API_PORT/docs"
say "Press Ctrl+C to stop both."

# Exit (and clean up) as soon as either process stops.
wait -n "${PIDS[@]}"

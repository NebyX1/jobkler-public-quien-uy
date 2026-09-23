#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"
STATE_DIR="$ROOT_DIR/.jobkler"
LOG_DIR="$ROOT_DIR/logs"
API_PID_FILE="$STATE_DIR/api.pid"
WEB_PID_FILE="$STATE_DIR/web.pid"
INDEXER_PID_FILE="$STATE_DIR/indexer.pid"
API_PORT_ARG=()
WEB_PORT_ARG=()
NO_WAIT=0
API_PID=""
WEB_PID=""
INDEXER_PID=""
KEEP_RUNNING=0
STOPPED=0

while (($#)); do
  case "$1" in
    --api-port) (($# >= 2)) || { echo 'Falta el puerto API.' >&2; exit 2; }; API_PORT_ARG=(--api-port "$2"); shift 2 ;;
    --web-port) (($# >= 2)) || { echo 'Falta el puerto web.' >&2; exit 2; }; WEB_PORT_ARG=(--web-port "$2"); shift 2 ;;
    --no-wait) NO_WAIT=1; shift ;;
    *) echo "Opción desconocida: $1" >&2; exit 2 ;;
  esac
done

stop_started() {
  [[ "$STOPPED" == 1 ]] && return 0
  STOPPED=1
  bash "$ROOT_DIR/stop.sh" || true
}
cleanup() {
  if [[ "$KEEP_RUNNING" != 1 ]]; then stop_started; fi
}
trap cleanup EXIT
trap 'KEEP_RUNNING=0; exit 130' INT
trap 'KEEP_RUNNING=0; exit 143' TERM

NODE_BIN="$(command -v node || true)"
[[ -n "$NODE_BIN" ]] || { echo 'Node.js 22.15.1 es necesario.' >&2; exit 2; }
NODE_VERSION="$("$NODE_BIN" -p 'process.versions.node')"
IFS=. read -r NODE_MAJOR NODE_MINOR _ <<< "$NODE_VERSION"
if [[ "$NODE_MAJOR" != 22 || "$NODE_MINOR" -lt 12 ]]; then
  echo "Node.js $NODE_VERSION no es compatible; se requiere Node 22.15.1 o 22.12+." >&2
  exit 2
fi
PYTHON="$(command -v python3.11 || true)"
[[ -n "$PYTHON" ]] || { echo 'Se necesita Python 3.11 (python3.11).' >&2; exit 2; }
"$PYTHON" -c 'import sys; assert sys.version_info[:2] == (3, 11)' || { echo 'La versión de Python debe ser 3.11.' >&2; exit 2; }

cd "$ROOT_DIR"
"$PYTHON" "$ROOT_DIR/scripts/prepare_local.py"
mapfile -t SETTINGS < <("$PYTHON" "$ROOT_DIR/scripts/local_ports.py" "${API_PORT_ARG[@]}" "${WEB_PORT_ARG[@]}")
[[ "${#SETTINGS[@]}" -ge 3 ]] || { echo 'No se pudieron resolver los puertos locales.' >&2; exit 2; }
API_PORT="${SETTINGS[0]}"
WEB_PORT="${SETTINGS[1]}"
FRONTEND_URL="${SETTINGS[2]}"
FRONTEND_ORIGIN="${FRONTEND_URL%/}"
API_URL="http://127.0.0.1:$API_PORT"

owns_process() {
  local pid_file="$1" expected="$2" cwd_expected="$3"
  [[ -f "$pid_file" ]] || return 1
  local pid args cwd
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  args="$(ps -p "$pid" -o args= 2>/dev/null || true)"
  cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
  [[ "$args" == *"$expected"* && "$cwd" == "$cwd_expected" ]]
}

if owns_process "$API_PID_FILE" "$BACKEND_DIR/wsgi.py" "$BACKEND_DIR" && owns_process "$WEB_PID_FILE" "$ROOT_DIR/node_modules/vite/bin/vite.js" "$ROOT_DIR"; then
  echo "Jobkler ya está iniciado en $FRONTEND_URL."
  echo "Logs: $LOG_DIR"
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "$FRONTEND_URL" >/dev/null 2>&1 || true; fi
  if [[ "$NO_WAIT" == 0 ]]; then
    echo 'Presioná Ctrl+C para salir de este seguimiento. Los servicios siguen bajo control de stop.sh.'
    while kill -0 "$(cat "$API_PID_FILE")" 2>/dev/null && kill -0 "$(cat "$WEB_PID_FILE")" 2>/dev/null; do sleep 2; done
  fi
  KEEP_RUNNING=1
  trap - EXIT INT TERM
  exit 0
fi

check_port() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    if ss -H -ltn "sport = :$port" 2>/dev/null | grep -q .; then return 1; fi
    return 0
  fi
  "$PYTHON" - "$port" <<'PY'
import socket, sys
s = socket.socket()
try:
    s.bind(("127.0.0.1", int(sys.argv[1])))
except OSError:
    raise SystemExit(1)
finally:
    s.close()
PY
}
check_port "$API_PORT" || { echo "El puerto API $API_PORT está ocupado. Jobkler no detuvo ese proceso." >&2; exit 2; }
check_port "$WEB_PORT" || { echo "El puerto web $WEB_PORT está ocupado. Jobkler no detuvo ese proceso." >&2; exit 2; }

mkdir -p "$STATE_DIR" "$LOG_DIR" "$BACKEND_DIR/instance"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON" -m venv "$VENV_DIR"
fi
VENV_PYTHON="$VENV_DIR/bin/python"
REQ="$BACKEND_DIR/requirements.txt"
STAMP="$VENV_DIR/.requirements-installed"
if [[ ! -f "$STAMP" || "$REQ" -nt "$STAMP" ]]; then
  "$VENV_PYTHON" -m pip install -r "$REQ"
  date -Is > "$STAMP"
fi

LOCK="$ROOT_DIR/package-lock.json"
INSTALLED_LOCK="$ROOT_DIR/node_modules/.package-lock.json"
if [[ ! -f "$INSTALLED_LOCK" || "$LOCK" -nt "$INSTALLED_LOCK" ]]; then
  (cd "$ROOT_DIR" && npm ci)
fi

export APP_ENV=development
export APP_HOST=127.0.0.1
export APP_PORT="$API_PORT"
export FRONTEND_URL="$FRONTEND_ORIGIN"
export FUSIONAUTH_REDIRECT_URI="http://127.0.0.1:$API_PORT/api/auth/callback"
export AUTH_ALLOWED_REDIRECT_URLS="$FRONTEND_ORIGIN"
export JOBKLER_API_TARGET="$API_URL"
export VITE_PORT="$WEB_PORT"

(cd "$BACKEND_DIR" && "$VENV_PYTHON" -m flask --app wsgi:app db upgrade)
(cd "$BACKEND_DIR" && "$VENV_PYTHON" -m flask --app wsgi:app seed-jobkler)
(cd "$BACKEND_DIR" && "$VENV_PYTHON" -m flask --app wsgi:app seed-search-fixtures)
(cd "$BACKEND_DIR" && "$VENV_PYTHON" -m flask --app wsgi:app search-rebuild)
MODEL_READY=0
if (cd "$BACKEND_DIR" && "$VENV_PYTHON" -m flask --app wsgi:app search-model-prepare); then
  MODEL_READY=1
else
  echo 'El encoder no está listo; la búsqueda avanzada seguirá disponible por texto y mostrará su modo reducido.' >&2
fi
(cd "$BACKEND_DIR" && "$VENV_PYTHON" -m flask --app wsgi:app search-check-llm)

(
  cd "$BACKEND_DIR"
  exec nohup env APP_ENV="$APP_ENV" APP_HOST="$APP_HOST" APP_PORT="$APP_PORT" FRONTEND_URL="$FRONTEND_URL" FUSIONAUTH_REDIRECT_URI="$FUSIONAUTH_REDIRECT_URI" AUTH_ALLOWED_REDIRECT_URLS="$AUTH_ALLOWED_REDIRECT_URLS" "$VENV_PYTHON" "$BACKEND_DIR/wsgi.py"
) >"$LOG_DIR/api.log" 2>"$LOG_DIR/api-error.log" </dev/null &
API_PID=$!
printf '%s\n' "$API_PID" > "$API_PID_FILE"
"$PYTHON" "$ROOT_DIR/scripts/wait_for_local.py" "$API_URL/api/health/ready" --ready-json --timeout 45

if [[ "$MODEL_READY" == 1 ]]; then
  (
    cd "$BACKEND_DIR"
    exec nohup env APP_ENV="$APP_ENV" APP_HOST="$APP_HOST" APP_PORT="$APP_PORT" FRONTEND_URL="$FRONTEND_URL" "$VENV_PYTHON" -m flask --app wsgi:app search-worker
  ) >"$LOG_DIR/indexer.log" 2>"$LOG_DIR/indexer-error.log" </dev/null &
  INDEXER_PID=$!
  printf '%s\n' "$INDEXER_PID" > "$INDEXER_PID_FILE"
  sleep 2
  if ! kill -0 "$INDEXER_PID" 2>/dev/null; then
    echo 'El worker de indexación no quedó activo; revisá logs/indexer-error.log.' >&2
    INDEXER_PID=""
    rm -f -- "$INDEXER_PID_FILE"
  fi
fi

(
  cd "$ROOT_DIR"
  exec nohup env APP_PORT="$API_PORT" VITE_PORT="$WEB_PORT" JOBKLER_API_TARGET="$API_URL" "$NODE_BIN" "$ROOT_DIR/node_modules/vite/bin/vite.js" --host 127.0.0.1 --port "$WEB_PORT" --strictPort
) >"$LOG_DIR/web.log" 2>"$LOG_DIR/web-error.log" </dev/null &
WEB_PID=$!
printf '%s\n' "$WEB_PID" > "$WEB_PID_FILE"
"$PYTHON" "$ROOT_DIR/scripts/wait_for_local.py" "$FRONTEND_URL" --timeout 45

echo "Jobkler está listo: $FRONTEND_URL"
echo "Flask readiness: $API_URL/api/health/ready"
echo "Logs: $LOG_DIR"
if [[ -n "$INDEXER_PID" ]]; then echo 'Indexador semántico local: activo.'; fi
if command -v xdg-open >/dev/null 2>&1; then xdg-open "$FRONTEND_URL" >/dev/null 2>&1 || true; fi
KEEP_RUNNING=1
if [[ "$NO_WAIT" == 1 ]]; then
  trap - EXIT INT TERM
  exit 0
fi
echo 'Presioná Ctrl+C para detener solo los procesos de Jobkler.'
while kill -0 "$API_PID" 2>/dev/null && kill -0 "$WEB_PID" 2>/dev/null; do sleep 2; done
KEEP_RUNNING=0
echo 'Un servicio Jobkler se detuvo; revisá logs/.'
exit 1

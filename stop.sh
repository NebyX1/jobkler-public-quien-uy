#!/usr/bin/env bash
set -u

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
STATE_DIR="$ROOT_DIR/.jobkler"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"

stop_one() {
  local name="$1"
  local script_path="$2"
  local expected_cwd="$3"
  local pid_file="$STATE_DIR/$name.pid"
  [[ -f "$pid_file" ]] || return 0
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [[ ! "$pid" =~ ^[0-9]+$ ]]; then
    rm -f -- "$pid_file"
    return 0
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    rm -f -- "$pid_file"
    printf '%s: proceso ya detenido.\n' "$name"
    return 0
  fi
  local args cwd
  args="$(ps -p "$pid" -o args= 2>/dev/null || true)"
  cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
  if [[ "$args" != *"$script_path"* || "$cwd" != "$expected_cwd" ]]; then
    rm -f -- "$pid_file"
    printf 'Advertencia: PID de %s no coincide con el proceso Jobkler registrado; no se detuvo.\n' "$name" >&2
    return 0
  fi
  kill -TERM "$pid" 2>/dev/null || true
  for _ in {1..20}; do
    if ! kill -0 "$pid" 2>/dev/null; then break; fi
    args="$(ps -p "$pid" -o args= 2>/dev/null || true)"
    cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
    if [[ "$args" != *"$script_path"* || "$cwd" != "$expected_cwd" ]]; then break; fi
    sleep 0.25
  done
  if kill -0 "$pid" 2>/dev/null; then
    args="$(ps -p "$pid" -o args= 2>/dev/null || true)"
    cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
    if [[ "$args" == *"$script_path"* && "$cwd" == "$expected_cwd" ]]; then
      kill -KILL "$pid" 2>/dev/null || true
    fi
  fi
  rm -f -- "$pid_file"
  printf '%s detenido.\n' "$name"
}

if [[ ! -d "$STATE_DIR" ]]; then
  printf 'No hay procesos Jobkler registrados.\n'
  exit 0
fi
stop_one indexer "$VENV_DIR/bin/python" "$BACKEND_DIR"
stop_one web "$ROOT_DIR/node_modules/vite/bin/vite.js" "$ROOT_DIR"
stop_one api "$ROOT_DIR/backend/wsgi.py" "$ROOT_DIR/backend"
if [[ -f "$STATE_DIR/ai-engine.pid" ]]; then
  ENGINE_PYTHON="$VENV_DIR/bin/python"
  if [[ ! -x "$ENGINE_PYTHON" ]]; then ENGINE_PYTHON="$(command -v python3.11 || true)"; fi
  if [[ -n "$ENGINE_PYTHON" ]]; then
    "$ENGINE_PYTHON" "$ROOT_DIR/ai-engine/engine.py" stop
  else
    printf 'No hay Python disponible para verificar y detener el motor local.\n' >&2
  fi
fi

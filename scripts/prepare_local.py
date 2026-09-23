#!/usr/bin/env python3
"""Create local configuration when absent and validate its safety before startup."""
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
template = BACKEND / ".env.example"
configured_path = os.environ.get("JOBKLER_ENV_FILE")
env_path = Path(configured_path) if configured_path else BACKEND / ".env"
if not env_path.is_absolute():
    env_path = ROOT / env_path

if not env_path.exists():
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    try:
        env_path.chmod(0o600)
    except OSError:
        pass
    print(f"Configuración local creada en {env_path.relative_to(ROOT)}.")

lines = env_path.read_text(encoding="utf-8").splitlines()
values = {}
for line in lines:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        continue
    key, value = stripped.split("=", 1)
    values[key.strip()] = value.strip().strip('"').strip("'")

def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)

if os.environ.get("DATABASE_URI") or (values.get("DATABASE_URI") and not values.get("DATABASE_URL")):
    fail("Encontré DATABASE_URI heredada sin DATABASE_URL. No se abrirá esa base. Guardá la configuración existente y prepará un archivo local separado desde backend/.env.example.")
if os.environ.get("DATABASE_URL", values.get("DATABASE_URL", "sqlite:///jobkler-demo.sqlite3")) != "sqlite:///jobkler-demo.sqlite3":
    fail("DATABASE_URL no apunta a la SQLite local de demo. Se detuvo antes de migrar o sembrar. Conservá esa configuración y usá JOBKLER_ENV_FILE con una configuración local separada.")
if os.environ.get("APP_ENV", values.get("APP_ENV", "production")).lower() != "development":
    fail("APP_ENV no es development. Se detuvo sin ejecutar migraciones; usá una configuración local separada para la demo.")
if os.environ.get("APP_HOST", values.get("APP_HOST", "127.0.0.1")) != "127.0.0.1":
    fail("APP_HOST debe ser 127.0.0.1 para mantener API y Vite en el mismo host local.")
mode = os.environ.get("AUTH_MODE", values.get("AUTH_MODE", "fusionauth")).lower()
if mode not in {"demo", "fusionauth"}:
    fail("AUTH_MODE debe ser demo o fusionauth.")
if mode == "demo" and os.environ.get("ALLOW_DEMO_AUTH", values.get("ALLOW_DEMO_AUTH", "")).lower() not in {"true", "1", "yes", "on"}:
    fail("AUTH_MODE=demo requiere ALLOW_DEMO_AUTH=true.")
ai_search_enabled = values.get("AI_SEARCH_ENABLED", "false").lower() in {"true", "1", "yes", "on"}
if ai_search_enabled and (mode != "demo" or values.get("ALLOW_DEMO_AUTH", "").lower() not in {"true", "1", "yes", "on"}):
    fail("AI_SEARCH_ENABLED solo puede usarse en la demo local autenticada de esta entrega.")
from urllib.parse import urlsplit
frontend = urlsplit(os.environ.get("FRONTEND_URL", values.get("FRONTEND_URL", "http://127.0.0.1:5173")))
if frontend.scheme != "http" or frontend.hostname != "127.0.0.1" or frontend.path not in {"", "/"}:
    fail("FRONTEND_URL debe usar http://127.0.0.1 con una ruta vacía para el modo local.")

secret_keys = ("SECRET_KEY", "AUTH_SESSION_SECRET", "CSRF_SECRET")
new_lines = []
seen = set()
for line in lines:
    stripped = line.strip()
    if "=" in stripped and not stripped.startswith("#"):
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key in secret_keys:
            seen.add(key)
            if not value.strip().strip('"').strip("'"):
                line = f"{key}={secrets.token_urlsafe(48)}"
                values[key] = line.split("=", 1)[1]
    new_lines.append(line)
for key in secret_keys:
    if key not in seen:
        generated = secrets.token_urlsafe(48)
        new_lines.append(f"{key}={generated}")
        values[key] = generated
if new_lines != lines:
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    try:
        env_path.chmod(0o600)
    except OSError:
        pass

if not all(values.get(key) for key in secret_keys):
    fail("No se pudieron preparar los secretos locales.")
print("Configuración segura para uso local; la base seleccionada es la SQLite de demo.")

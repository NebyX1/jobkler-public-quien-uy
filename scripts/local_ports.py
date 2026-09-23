#!/usr/bin/env python3
"""Print safe local runtime settings; never prints credentials."""
import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
env_path = Path(os.environ.get("JOBKLER_ENV_FILE", BACKEND / ".env"))
if not env_path.is_absolute():
    env_path = ROOT / env_path
values = {}
for line in env_path.read_text(encoding="utf-8").splitlines():
    raw = line.strip()
    if raw and not raw.startswith("#") and "=" in raw:
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

parser = argparse.ArgumentParser()
parser.add_argument("--api-port", type=int)
parser.add_argument("--web-port", type=int)
args = parser.parse_args()
api_port = args.api_port or int(os.environ.get("APP_PORT", values.get("APP_PORT", "5000")))
base = urlsplit(os.environ.get("FRONTEND_URL", values.get("FRONTEND_URL", "http://127.0.0.1:5173")))
if base.scheme != "http" or base.hostname != "127.0.0.1":
    raise SystemExit("FRONTEND_URL debe usar http://127.0.0.1 en modo local.")
web_port = args.web_port or int(os.environ.get("VITE_PORT", str(base.port or 5173)))
frontend = urlunsplit(("http", f"127.0.0.1:{web_port}", "", "", ""))
if not (1 <= api_port <= 65535 and 1 <= web_port <= 65535):
    raise SystemExit("Los puertos deben estar entre 1 y 65535.")
for value in (str(api_port), str(web_port), frontend):
    print(value)

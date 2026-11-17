#!/usr/bin/env python3
"""Configure and supervise Jobkler's local, authenticated llama.cpp server."""

import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener

ENGINE_DIR = Path(__file__).resolve().parent
ROOT = ENGINE_DIR.parent
STATE_FILE = ROOT / ".jobkler" / "ai-engine.pid"
ENGINE_ENV = ENGINE_DIR / ".env"
DEFAULT_ALIAS = "Qwen3.5-2B-Q4_K_M.gguf"
DEFAULT_URL = "http://127.0.0.1:8081/v1"


class EngineError(RuntimeError):
    pass


def backend_env_path():
    path = Path(os.environ.get("JOBKLER_ENV_FILE", ROOT / "backend" / ".env")).expanduser()
    return path if path.is_absolute() else ROOT / path


def read_env(path):
    values = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def write_missing_key(path, key, value):
    """Fill only an absent or empty secret, preserving other local settings."""
    lines = path.read_text(encoding="utf-8").splitlines()
    result = []
    found = False
    for line in lines:
        raw = line.strip()
        if raw and not raw.startswith("#") and "=" in raw and raw.split("=", 1)[0].strip() == key:
            found = True
            if not raw.split("=", 1)[1].strip().strip('"').strip("'"):
                line = f"{key}={value}"
        result.append(line)
    if not found:
        result.append(f"{key}={value}")
    path.write_text("\n".join(result) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def value(values, key, default=""):
    return os.environ.get(key, values.get(key, default)).strip()


def is_managed(values):
    return value(values, "AI_LLM_MANAGED", "true").lower() in {"1", "true", "yes", "on"}


def prepare():
    backend_path = backend_env_path()
    if not backend_path.is_file():
        raise EngineError("Falta la configuración del backend; iniciá Jobkler desde su carpeta raíz.")
    backend = read_env(backend_path)
    if not is_managed(backend):
        return {"managed": False}
    if not ENGINE_ENV.exists():
        template = ENGINE_DIR / ".env.example"
        ENGINE_ENV.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
        try:
            ENGINE_ENV.chmod(0o600)
        except OSError:
            pass
    engine = read_env(ENGINE_ENV)
    backend_key = value(backend, "AI_LLM_API_KEY")
    engine_key = value(engine, "LLM_API_KEY")
    if not backend_key.isascii() or not engine_key.isascii():
        raise EngineError("Las claves del motor deben usar caracteres ASCII.")
    if backend_key and engine_key and not secrets.compare_digest(backend_key, engine_key):
        raise EngineError("AI_LLM_API_KEY y LLM_API_KEY no coinciden; revisá los archivos .env sin publicar las claves.")
    key = backend_key or engine_key or secrets.token_urlsafe(48)
    if len(key) < 32:
        raise EngineError("La clave local del motor debe tener al menos 32 caracteres.")
    if not backend.get("AI_LLM_API_KEY"):
        write_missing_key(backend_path, "AI_LLM_API_KEY", key)
    if not engine.get("LLM_API_KEY"):
        write_missing_key(ENGINE_ENV, "LLM_API_KEY", key)
    return {"managed": True}


def settings():
    backend = read_env(backend_env_path())
    if not is_managed(backend):
        return None
    engine = read_env(ENGINE_ENV)
    key = value(backend, "AI_LLM_API_KEY")
    engine_key = value(engine, "LLM_API_KEY")
    if not key.isascii() or not engine_key.isascii():
        raise EngineError("Las claves del motor deben usar caracteres ASCII.")
    if not key or not engine_key or not secrets.compare_digest(key, engine_key):
        raise EngineError("Las claves del backend y del motor no coinciden; ejecutá la preparación local.")
    base_url = value(backend, "AI_LLM_BASE_URL", DEFAULT_URL).rstrip("/")
    url = urlsplit(base_url)
    try:
        port = int(value(engine, "LLM_PORT", "8081"))
        url_port = url.port or 80
        context = int(value(engine, "LLM_CONTEXT", "4096"))
        threads = int(value(engine, "LLM_THREADS", "4"))
        gpu_layers = int(value(engine, "LLM_GPU_LAYERS", "0"))
    except ValueError as exc:
        raise EngineError("El puerto, contexto, hilos y capas GPU del motor deben ser números válidos.") from exc
    if (url.scheme != "http" or url.hostname != "127.0.0.1" or url.path.rstrip("/") != "/v1"
            or url.query or url.fragment or url.username or url.password
            or value(engine, "LLM_HOST", "127.0.0.1") != "127.0.0.1" or url_port != port):
        raise EngineError("El motor administrado requiere 127.0.0.1 y el mismo puerto en ambos archivos .env.")
    if not (1 <= port <= 65535 and context > 0 and threads > 0 and gpu_layers >= 0):
        raise EngineError("La configuración numérica del motor está fuera de rango.")
    alias = value(engine, "LLM_MODEL_ALIAS", DEFAULT_ALIAS)
    if not alias or value(backend, "AI_LLM_MODEL", DEFAULT_ALIAS) != alias:
        raise EngineError("AI_LLM_MODEL debe coincidir con LLM_MODEL_ALIAS en ai-engine/.env.")
    model = Path(value(engine, "LLM_MODEL", f"models/{DEFAULT_ALIAS}"))
    if not model.is_absolute():
        model = ENGINE_DIR / model
    server = ENGINE_DIR / "bin" / ("llama-server.exe" if os.name == "nt" else "llama-server")
    return {"base_url": base_url, "key": key, "port": port, "alias": alias, "model": model.resolve(),
            "server": server.resolve(), "context": context, "threads": threads, "gpu_layers": gpu_layers}


def identity(pid):
    """Read the executable and OS creation identity; never trust a PID alone."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.QueryFullProcessImageNameW.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
        kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel.GetProcessTimes.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME))
        kernel.GetProcessTimes.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            size = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            created, exited, kernel_time, user_time = (wintypes.FILETIME() for _ in range(4))
            if not kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return None
            if not kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(kernel_time), ctypes.byref(user_time)):
                return None
            if exited.dwLowDateTime or exited.dwHighDateTime:
                return None
            created_ticks = (created.dwHighDateTime << 32) | created.dwLowDateTime
            return {"executable": os.path.normcase(os.path.realpath(buffer.value)), "created": str(created_ticks)}
        finally:
            kernel.CloseHandle(handle)
    try:
        executable = os.path.realpath(f"/proc/{pid}/exe")
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        if fields[0] == "Z":
            return None
        return {"executable": executable, "created": fields[19]}
    except (OSError, IndexError):
        return None


def read_record():
    try:
        result = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(result, dict) or not isinstance(result.get("pid"), int) or result["pid"] <= 0:
            return None
        return result
    except (OSError, ValueError):
        return None


def owned(record):
    if not record:
        return False
    actual = identity(record["pid"])
    expected_path = os.path.normcase(os.path.realpath(ENGINE_DIR / "bin" / ("llama-server.exe" if os.name == "nt" else "llama-server")))
    return bool(actual and actual == {"executable": record.get("executable"), "created": record.get("created")}
                and actual["executable"] == expected_path)


def model_ready(config):
    request = Request(config["base_url"] + "/models", headers={"Authorization": "Bearer " + config["key"]})
    try:
        with build_opener(ProxyHandler({})).open(request, timeout=2) as response:
            data = json.load(response)
        return any(item.get("id") == config["alias"] for item in data.get("data", []) if isinstance(item, dict))
    except (OSError, ValueError, URLError):
        return False


def wait_ready(config, record, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not owned(record):
            raise EngineError("El proceso del motor terminó durante el arranque; revisá logs/ai-engine-error.log.")
        if model_ready(config):
            return
        time.sleep(0.5)
    raise EngineError("El motor no alcanzó el estado listo; revisá logs/ai-engine-error.log.")


def stop():
    record = read_record()
    if not record:
        return {"stopped": False}
    if not owned(record):
        STATE_FILE.unlink(missing_ok=True)
        return {"stopped": False, "stale_record": True}
    os.kill(record["pid"], signal.SIGTERM)
    deadline = time.monotonic() + 6
    while owned(record) and time.monotonic() < deadline:
        time.sleep(0.1)
    if owned(record) and os.name != "nt":
        os.kill(record["pid"], signal.SIGKILL)
        deadline = time.monotonic() + 3
        while owned(record) and time.monotonic() < deadline:
            time.sleep(0.1)
    if owned(record):
        raise EngineError("No se pudo detener el motor que inició Jobkler.")
    STATE_FILE.unlink(missing_ok=True)
    return {"stopped": True}


def start():
    preparation = prepare()
    if not preparation["managed"]:
        return {"managed": False, "started": False}
    config = settings()
    if not config["server"].is_file():
        raise EngineError(f"Falta el ejecutable del motor: {config['server']}. Consultá ai-engine/README.md.")
    if not config["model"].is_file():
        raise EngineError(f"Falta el modelo GGUF: {config['model']}. Consultá ai-engine/README.md.")
    record = read_record()
    if owned(record):
        wait_ready(config, record)
        return {"managed": True, "started": False, "pid": record["pid"]}
    with socket.socket() as listener:
        try:
            listener.bind(("127.0.0.1", config["port"]))
        except OSError as exc:
            raise EngineError(f"El puerto del motor {config['port']} está ocupado; no se detuvo ningún proceso ajeno.") from exc

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    logs = ROOT / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    args = [str(config["server"]), "-m", str(config["model"]), "--alias", config["alias"],
            "--host", "127.0.0.1", "--port", str(config["port"]), "-c", str(config["context"]),
            "-np", "1", "-t", str(config["threads"]), "-tb", str(config["threads"]),
            "-ngl", str(config["gpu_layers"]), "--no-cache-prompt", "--reasoning", "off", "--metrics"]
    env = os.environ.copy()
    env["LLAMA_API_KEY"] = config["key"]
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == "nt" else 0
    with (logs / "ai-engine.log").open("a", encoding="utf-8") as out, (logs / "ai-engine-error.log").open("a", encoding="utf-8") as err:
        process = subprocess.Popen(args, cwd=ENGINE_DIR, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                   creationflags=flags, start_new_session=os.name != "nt")
    try:
        info = identity(process.pid)
        if not info:
            raise EngineError("No se pudo identificar el proceso del motor recién iniciado.")
        record = {"pid": process.pid, **info}
        STATE_FILE.write_text(json.dumps(record) + "\n", encoding="utf-8")
    except Exception:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        raise
    try:
        wait_ready(config, record)
    except Exception:
        stop()
        raise
    return {"managed": True, "started": True, "pid": process.pid}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"prepare", "start", "stop", "status"}:
        raise EngineError("Uso: python ai-engine/engine.py prepare|start|stop|status")
    command = sys.argv[1]
    if command == "prepare":
        result = prepare()
    elif command == "start":
        result = start()
    elif command == "stop":
        result = stop()
    else:
        record = read_record()
        result = {"running": owned(record), "pid": record["pid"] if owned(record) else None}
        if result["running"]:
            config = settings()
            result["ready"] = bool(config and model_ready(config))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (EngineError, OSError) as exc:
        print(f"Error del motor local: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

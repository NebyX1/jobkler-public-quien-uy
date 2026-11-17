import os
from pathlib import Path

from .search.model_manifest import MODEL_NAME, MODEL_REVISION

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
INSTANCE_DIR = BACKEND_DIR / "instance"
ENV_FILE = Path(os.environ.get("JOBKLER_ENV_FILE", BACKEND_DIR / ".env")).expanduser()
if not ENV_FILE.is_absolute():
    ENV_FILE = BACKEND_DIR.parent / ENV_FILE
load_dotenv(ENV_FILE, override=False)


def as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    APP_ENV = (os.environ.get("APP_ENV") or os.environ.get("FLASK_ENV") or "production").strip().lower()
    ENV_NAME = APP_ENV
    AUTH_MODE = os.environ.get("AUTH_MODE", "fusionauth").strip().lower()
    ALLOW_DEMO_AUTH = as_bool(os.environ.get("ALLOW_DEMO_AUTH"), False)
    AI_SEARCH_ENABLED = as_bool(os.environ.get("AI_SEARCH_ENABLED"), False)
    AI_LLM_BASE_URL = os.environ.get("AI_LLM_BASE_URL", "http://127.0.0.1:8081/v1").rstrip("/")
    AI_LLM_MODEL = os.environ.get("AI_LLM_MODEL", "Qwen3.5-2B-Q4_K_M.gguf").strip()
    AI_LLM_API_KEY = os.environ.get("AI_LLM_API_KEY", "").strip()
    AI_SEARCH_TIMEOUT_SECONDS = float(os.environ.get("AI_SEARCH_TIMEOUT_SECONDS", "20"))
    AI_SEARCH_CONNECT_TIMEOUT_SECONDS = float(os.environ.get("AI_SEARCH_CONNECT_TIMEOUT_SECONDS", "2"))
    AI_SEARCH_QUEUE_WAIT_SECONDS = float(os.environ.get("AI_SEARCH_QUEUE_WAIT_SECONDS", "10"))
    AI_SEARCH_RATE_LIMIT_PER_HOUR = int(os.environ.get("AI_SEARCH_RATE_LIMIT_PER_HOUR", "20"))
    AI_SEARCH_SEMANTIC_ENABLED = as_bool(os.environ.get("AI_SEARCH_SEMANTIC_ENABLED"), True)
    AI_SEARCH_SEMANTIC_MIN_COSINE = float(os.environ.get("AI_SEARCH_SEMANTIC_MIN_COSINE", "0.54"))
    AI_SEARCH_EMBEDDING_THREADS = int(os.environ.get("AI_SEARCH_EMBEDDING_THREADS", "2"))
    AI_SEARCH_MAX_RESULTS = int(os.environ.get("AI_SEARCH_MAX_RESULTS", "20"))
    AI_SEARCH_DEFAULT_RESULTS = int(os.environ.get("AI_SEARCH_DEFAULT_RESULTS", "10"))
    AI_SEARCH_MAX_QUERY_CHARS = int(os.environ.get("AI_SEARCH_MAX_QUERY_CHARS", "500"))
    AI_SEARCH_ENCODER_MODEL = os.environ.get("AI_SEARCH_ENCODER_MODEL", MODEL_NAME)
    AI_SEARCH_ENCODER_REVISION = os.environ.get("AI_SEARCH_ENCODER_REVISION", MODEL_REVISION)
    AI_SEARCH_ENCODER_CACHE = os.environ.get("AI_SEARCH_ENCODER_CACHE") or str(INSTANCE_DIR / "fastembed")
    APP_HOST = os.environ.get("APP_HOST", "127.0.0.1").strip()
    APP_PORT = int(os.environ.get("APP_PORT", "5000"))
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:5173").rstrip("/")
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    AUTH_SESSION_SECRET = os.environ.get("AUTH_SESSION_SECRET", SECRET_KEY)
    CSRF_SECRET = os.environ.get("CSRF_SECRET", SECRET_KEY)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///jobkler-demo.sqlite3")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    AUTH_COOKIE_NAME = os.environ.get("AUTH_COOKIE_NAME", "jobkler_session")
    CSRF_COOKIE_NAME = os.environ.get("CSRF_COOKIE_NAME", "jobkler_csrf")
    AUTH_COOKIE_SECURE = as_bool(os.environ.get("AUTH_COOKIE_SECURE"), APP_ENV == "production")
    AUTH_COOKIE_SAMESITE = os.environ.get("AUTH_COOKIE_SAMESITE", "Lax")
    SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "86400"))
    FUSIONAUTH_BASE_URL = os.environ.get("FUSIONAUTH_BASE_URL", "").rstrip("/")
    FUSIONAUTH_ISSUER = os.environ.get("FUSIONAUTH_ISSUER", "").rstrip("/")
    FUSIONAUTH_CLIENT_ID = os.environ.get("FUSIONAUTH_CLIENT_ID", "").strip()
    FUSIONAUTH_CLIENT_SECRET = os.environ.get("FUSIONAUTH_CLIENT_SECRET", "").strip()
    FUSIONAUTH_GOOGLE_IDP_ID = os.environ.get("FUSIONAUTH_GOOGLE_IDP_ID", "").strip()
    FUSIONAUTH_REDIRECT_URI = os.environ.get(
        "FUSIONAUTH_REDIRECT_URI", "http://127.0.0.1:5000/api/auth/callback"
    )
    AUTH_ALLOWED_REDIRECT_URLS = tuple(
        item.strip().rstrip("/") for item in os.environ.get("AUTH_ALLOWED_REDIRECT_URLS", FRONTEND_URL).split(",") if item.strip()
    )


def validate_runtime_config(app):
    cfg = app.config
    mode = cfg["AUTH_MODE"]
    if mode not in {"demo", "fusionauth"}:
        raise RuntimeError("AUTH_MODE debe ser demo o fusionauth.")
    if cfg["AI_SEARCH_ENABLED"]:
        if cfg["APP_ENV"] not in {"development", "testing"}:
            raise RuntimeError("La búsqueda avanzada solo se habilita en desarrollo local en esta entrega.")
        if not app.testing and (
            cfg["AUTH_MODE"] != "demo"
            or not cfg["ALLOW_DEMO_AUTH"]
            or cfg["SQLALCHEMY_DATABASE_URI"] != "sqlite:///jobkler-demo.sqlite3"
            or cfg["APP_HOST"] not in {"127.0.0.1", "localhost", "::1"}
        ):
            raise RuntimeError(
                "La búsqueda avanzada solo puede activarse con la demo local autenticada y su SQLite prevista."
            )
        if not (0.1 <= cfg["AI_SEARCH_TIMEOUT_SECONDS"] <= 60):
            raise RuntimeError("AI_SEARCH_TIMEOUT_SECONDS debe estar entre 0.1 y 60 segundos.")
        if not (0.1 <= cfg["AI_SEARCH_CONNECT_TIMEOUT_SECONDS"] <= 10):
            raise RuntimeError("AI_SEARCH_CONNECT_TIMEOUT_SECONDS debe estar entre 0.1 y 10 segundos.")
        if not (0.0 <= cfg["AI_SEARCH_QUEUE_WAIT_SECONDS"] <= 15.0):
            raise RuntimeError("AI_SEARCH_QUEUE_WAIT_SECONDS debe estar entre 0 y 15 segundos.")
        if not (1 <= cfg["AI_SEARCH_RATE_LIMIT_PER_HOUR"] <= 120):
            raise RuntimeError("AI_SEARCH_RATE_LIMIT_PER_HOUR debe estar entre 1 y 120.")
        if not (1 <= cfg["AI_SEARCH_EMBEDDING_THREADS"] <= 8):
            raise RuntimeError("AI_SEARCH_EMBEDDING_THREADS debe estar entre 1 y 8.")
        if cfg["AI_SEARCH_MAX_RESULTS"] > 20 or cfg["AI_SEARCH_DEFAULT_RESULTS"] > cfg["AI_SEARCH_MAX_RESULTS"]:
            raise RuntimeError("El máximo de resultados avanzados es 20 y debe cubrir el valor predeterminado.")
        if not (2 <= cfg["AI_SEARCH_MAX_QUERY_CHARS"] <= 500):
            raise RuntimeError("AI_SEARCH_MAX_QUERY_CHARS debe estar entre 2 y 500.")
        if not (0.0 <= cfg["AI_SEARCH_SEMANTIC_MIN_COSINE"] <= 1.0):
            raise RuntimeError("AI_SEARCH_SEMANTIC_MIN_COSINE debe estar entre 0 y 1.")
        if cfg["AI_SEARCH_ENCODER_MODEL"] != MODEL_NAME or cfg["AI_SEARCH_ENCODER_REVISION"] != MODEL_REVISION:
            raise RuntimeError("El encoder de búsqueda debe respetar la versión fijada en model_manifest.py.")

    if cfg["APP_ENV"] == "production":
        if mode == "demo" or cfg["ALLOW_DEMO_AUTH"]:
            raise RuntimeError("La autenticación demo solo se permite en desarrollo local.")
        for key in ("SECRET_KEY", "AUTH_SESSION_SECRET", "CSRF_SECRET"):
            value = str(cfg.get(key, "")).lower()
            if len(value) < 32 or "change-me" in value or "example" in value:
                raise RuntimeError(f"{key} debe configurarse con un secreto de producción.")
        if not cfg["AUTH_COOKIE_SECURE"]:
            raise RuntimeError("AUTH_COOKIE_SECURE=true es obligatorio en producción.")
        if mode == "fusionauth" and not all(
            cfg.get(key) and "example" not in str(cfg.get(key)).lower()
            for key in (
                "FUSIONAUTH_BASE_URL", "FUSIONAUTH_ISSUER", "FUSIONAUTH_CLIENT_ID",
                "FUSIONAUTH_CLIENT_SECRET", "FUSIONAUTH_GOOGLE_IDP_ID",
            )
        ):
            raise RuntimeError("Faltan credenciales reales de FusionAuth para producción.")

    if mode == "demo":
        if cfg["APP_ENV"] != "development" or not cfg["ALLOW_DEMO_AUTH"]:
            raise RuntimeError("Modo demo requiere APP_ENV=development y ALLOW_DEMO_AUTH=true.")
        if cfg["APP_HOST"] not in {"127.0.0.1", "localhost", "::1"}:
            raise RuntimeError("Modo demo solo puede escuchar en una interfaz loopback.")
        if not app.testing:
            uri = str(cfg["SQLALCHEMY_DATABASE_URI"])
            if uri != "sqlite:///jobkler-demo.sqlite3":
                raise RuntimeError(
                    "La demo local requiere DATABASE_URL=sqlite:///jobkler-demo.sqlite3; "
                    "no se ejecutarán migraciones ni seed sobre otra base."
                )
        if not cfg["SECRET_KEY"] or not cfg["AUTH_SESSION_SECRET"] or not cfg["CSRF_SECRET"]:
            raise RuntimeError("Faltan secretos locales. Iniciá con run.ps1/run.sh para generarlos.")

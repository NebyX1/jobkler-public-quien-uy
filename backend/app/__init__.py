from pathlib import Path

from flask import Flask, jsonify, request
from sqlalchemy import inspect, text

from .config import Config, INSTANCE_DIR, validate_runtime_config
from .extensions import db, limiter, migrate


def create_app(config_class=Config, overrides=None):
    app = Flask(__name__, instance_path=str(INSTANCE_DIR), instance_relative_config=True)
    app.config.from_object(config_class)
    if not app.config.get("MAX_CONTENT_LENGTH"):
        app.config["MAX_CONTENT_LENGTH"] = 8192
    if overrides:
        app.config.update(overrides)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    validate_runtime_config(app)

    db.init_app(app)
    migrate.init_app(app, db, directory=str(Path(__file__).resolve().parents[1] / "migrations"), compare_type=True)
    limiter.init_app(app)

    from . import models  # noqa: F401
    from .api.auth_routes import fusionauth_bp
    from .api.jobkler import jobkler_bp
    from .api.advanced_search import advanced_search_bp

    app.register_blueprint(jobkler_bp, url_prefix="/api")
    app.register_blueprint(advanced_search_bp, url_prefix="/api/search")
    app.register_blueprint(fusionauth_bp)
    from .commands import register_commands
    register_commands(app)

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    @app.get("/api/health/ready")
    def ready():
        try:
            with db.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            if not inspect(db.engine).has_table("accounts"):
                return {"status": "not_ready", "error": "schema_missing"}, 503
            if app.config["AI_SEARCH_ENABLED"]:
                required = ("profile_search_documents", "profile_search_chunks", "profile_search_index_jobs", "profile_coverages", "advanced_search_rate_events")
                if any(not inspect(db.engine).has_table(table) for table in required):
                    return {"status": "not_ready", "error": "advanced_search_schema_missing"}, 503
                with db.engine.connect() as connection:
                    connection.execute(text("SELECT count(*) FROM profile_search_fts")).scalar_one()
            return {"status": "ready", "database": "ok"}, 200
        except Exception:
            return {"status": "not_ready", "error": "database_unavailable"}, 503

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "Recurso no encontrado."}), 404

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"error": "La solicitud supera el tamaño permitido."}), 413

    @app.errorhandler(429)
    def too_many(_error):
        return jsonify({"error": "Demasiados intentos. Esperá un momento y probá de nuevo."}), 429

    @app.before_request
    def local_demo_loopback_only():
        if app.config["AUTH_MODE"] != "demo" or app.testing:
            return None
        if not request.remote_addr:
            return jsonify({"error": "La demo solo acepta conexiones locales."}), 403
        import ipaddress
        try:
            if not ipaddress.ip_address(request.remote_addr).is_loopback:
                return jsonify({"error": "La demo solo acepta conexiones locales."}), 403
        except ValueError:
            return jsonify({"error": "La demo solo acepta conexiones locales."}), 403
        return None

    return app

import os
import subprocess
import sys
import hashlib
import json
import platform
import time
import math
from datetime import datetime, timezone
from pathlib import Path

import click
import requests
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import func, select

from app.config import BACKEND_DIR, INSTANCE_DIR
from app.extensions import db


@click.command("seed-jobkler")
@with_appcontext
def seed_jobkler_command():
    """Insert the deterministic local Jobkler fixtures once."""
    if current_app.config["APP_ENV"] != "development" or current_app.config["SQLALCHEMY_DATABASE_URI"] != "sqlite:///jobkler-demo.sqlite3":
        raise click.ClickException("La semilla solo se permite sobre la base SQLite local de desarrollo.")
    from app.seed_data import seed_jobkler
    result = seed_jobkler()
    click.echo("Semilla Jobkler: " + ("sin cambios (ya inicializada)." if result["skipped"] else f"{result['profiles']} perfiles y {result['reviews']} reseñas creados."))


@click.command("reset-demo")
@click.option("--yes", is_flag=True, help="Confirma que querés borrar la base local de demostración.")
@with_appcontext
def reset_demo_command(yes):
    """Explicitly remove and rebuild only the local demo SQLite database."""
    cfg = current_app.config
    if cfg["APP_ENV"] != "development" or cfg["AUTH_MODE"] != "demo" or not cfg["ALLOW_DEMO_AUTH"]:
        raise click.ClickException("Reset cancelado: se requiere desarrollo con autenticación demo habilitada.")
    if cfg["SQLALCHEMY_DATABASE_URI"] != "sqlite:///jobkler-demo.sqlite3":
        raise click.ClickException("Reset cancelado: DATABASE_URL no apunta a la base local esperada.")
    database = (Path(current_app.instance_path) / "jobkler-demo.sqlite3").resolve()
    allowed = (Path(current_app.instance_path).resolve() / "jobkler-demo.sqlite3").resolve()
    if database != allowed or Path(current_app.instance_path).resolve() != INSTANCE_DIR.resolve():
        raise click.ClickException("Reset cancelado: la ruta de la base no coincide con backend/instance.")
    if not yes and not click.confirm(f"Esto elimina los datos locales de {database}. ¿Continuar?"):
        raise click.ClickException("Reset cancelado.")

    db.session.remove()
    db.engine.dispose()
    if database.exists():
        database.unlink()
    env = os.environ.copy()
    subprocess.run(
        [sys.executable, "-m", "flask", "--app", "wsgi:app", "db", "upgrade"],
        cwd=BACKEND_DIR, env=env, check=True,
    )
    from app.seed_data import seed_jobkler
    result = seed_jobkler()
    click.echo(f"Base local recreada mediante migraciones; {result['profiles']} perfiles ficticios y {result['reviews']} reseñas cargados.")


def require_local_search_database():
    cfg = current_app.config
    if cfg["APP_ENV"] != "development" or cfg["SQLALCHEMY_DATABASE_URI"] != "sqlite:///jobkler-demo.sqlite3":
        raise click.ClickException("La operación se permite solo en la SQLite local de desarrollo prevista.")


@click.command("seed-search-fixtures")
@with_appcontext
def seed_search_fixtures_command():
    """Insert synthetic advanced-search profiles once, without replacing existing rows."""
    require_local_search_database()
    from app.search.fixtures import seed_search_fixtures
    added = seed_search_fixtures()
    click.echo(f"Fixtures de búsqueda sintéticos: {added} perfiles nuevos.")


@click.command("seed-expanded-profiles")
@with_appcontext
def seed_expanded_profiles_command():
    """Add a broader fictional demo population once, with secondary work in biographies."""
    require_local_search_database()
    from app.search.expanded_fixtures import seed_expanded_profiles
    result = seed_expanded_profiles()
    if result["skipped"]:
        click.echo("Perfiles ficticios ampliados: sin cambios (ya inicializados).")
    else:
        click.echo(f"Perfiles ficticios ampliados: {result['profiles']} nuevos; {result['with_extra']} con trabajos adicionales en su descripción.")


@click.command("search-rebuild")
@click.option("--force", is_flag=True, help="Descarta embeddings y vuelve a encolar todas las revisiones activas.")
@with_appcontext
def search_rebuild_command(force):
    """Idempotently rebuild FTS documents, explicit coverage, and embedding jobs."""
    require_local_search_database()
    from app.models import Profile
    from app.search.catalog import resolve_coverage_values
    from app.search.documents import rebuild_search_documents
    for profile in db.session.scalars(db.select(Profile)).all():
        resolve_coverage_values(profile.id, profile.service_area)
    db.session.commit()
    count = rebuild_search_documents(force=force)
    click.echo(f"Documentos de búsqueda sincronizados: {count}; force={str(force).lower()}.")


@click.command("search-model-prepare")
@with_appcontext
def search_model_prepare_command():
    """Download and verify the pinned ONNX model under the ignored local instance cache."""
    require_local_search_database()
    from app.search.encoder import prepare_model
    path, metadata = prepare_model(current_app.config)
    click.echo(f"Encoder listo: {metadata['repository']}@{metadata['revision']}")
    click.echo(f"ONNX SHA-256: {metadata['sha256']}")
    click.echo(f"Caché: {path}")


@click.command("search-model-check")
@with_appcontext
def search_model_check_command():
    """Check only for the local pinned ONNX file; do not download it."""
    require_local_search_database()
    from app.search.encoder import model_directory
    from app.search.model_manifest import MODEL_FILE
    path = model_directory(current_app.config) / MODEL_FILE
    if not path.is_file():
        click.echo("Encoder local no preparado.")
        raise click.ClickException("Falta el modelo ONNX fijado.")
    click.echo(f"Encoder local preparado: {path}")


@click.command("search-index-once")
@with_appcontext
def search_index_once_command():
    """Process at most one due persistent embedding job."""
    require_local_search_database()
    from app.search.indexer import process_one
    state = process_one(config=current_app.config)
    click.echo(f"Resultado del indexador: {state}.")
    if state == "failed":
        raise click.ClickException("El trabajo falló; revisar `flask search-index-status` y los logs locales.")


@click.command("search-index-status")
@with_appcontext
def search_index_status_command():
    """Show persistent index job and current vector counts."""
    require_local_search_database()
    from sqlalchemy import func
    from app.models import ProfileSearchChunk, ProfileSearchIndexJob
    jobs = dict(db.session.execute(select(ProfileSearchIndexJob.status, func.count()).group_by(ProfileSearchIndexJob.status)).all())
    vectors = db.session.scalar(select(func.count(ProfileSearchChunk.chunk_id))) or 0
    click.echo("Trabajos: " + ", ".join(f"{key}={value}" for key, value in sorted(jobs.items())))
    click.echo(f"Fragmentos vectorizados vigentes almacenados: {vectors}")


@click.command("search-check-llm")
@with_appcontext
def search_check_llm_command():
    """Read the configured llama.cpp model list; never starts or changes that server."""
    from app.search.llm import authorization_headers
    base_url = current_app.config["AI_LLM_BASE_URL"].rstrip("/")
    try:
        with requests.Session() as session:
            session.trust_env = False
            session.headers.update(authorization_headers(current_app.config["AI_LLM_API_KEY"]))
            response = session.get(f"{base_url}/models", timeout=(2, 3))
        response.raise_for_status()
        models = response.json().get("data", [])
        identifiers = [item.get("id") for item in models if isinstance(item, dict) and item.get("id")]
        if current_app.config["AI_LLM_MODEL"] in identifiers:
            click.echo(f"Qwen local respondió; alias configurado presente: {current_app.config['AI_LLM_MODEL']}.")
        elif identifiers:
            click.echo("Qwen respondió, pero el alias configurado no aparece. Alias disponibles: " + ", ".join(identifiers))
            click.echo("La app quedará en modo determinista hasta corregir AI_LLM_MODEL.")
        else:
            click.echo("Qwen respondió sin modelos publicados; la app usará extracción determinista.")
    except Exception as exc:
        click.echo(f"Qwen local no está disponible ({type(exc).__name__}); la app usará extracción determinista.")


@click.command("search-worker")
@click.option("--poll-seconds", type=click.FloatRange(min=0.1, max=30), default=1.0)
@with_appcontext
def search_worker_command(poll_seconds):
    """Run the persistent-index queue in this dedicated process."""
    require_local_search_database()
    from app.search.indexer import run_worker
    run_worker(current_app._get_current_object(), poll_seconds=poll_seconds)


def _process_working_set_bytes():
    """Return the current CLI process working set where the OS exposes it."""
    try:
        if os.name == "nt":
            import ctypes

            class ProcessMemoryCounters(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(counters)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ok = ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
            return int(counters.WorkingSetSize) if ok else None
        import resource

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(peak if platform.system() == "Darwin" else peak * 1024)
    except (AttributeError, OSError, ImportError, ValueError):
        return None


def _metric_summary(values):
    finite = sorted(float(value) for value in values if value is not None and math.isfinite(float(value)))
    if not finite:
        return {"mean_ms": None, "p50_ms": None, "p95_ms": None}
    return {
        "mean_ms": round(sum(finite) / len(finite), 2),
        "p50_ms": round(finite[(len(finite) - 1) // 2], 2),
        "p95_ms": round(finite[min(len(finite) - 1, math.ceil(len(finite) * 0.95) - 1)], 2),
    }


def _retrieval_metrics(rows, *, field, status_field=None):
    cases = []
    recall_sum = 0.0
    recall_count = 0
    hits = 0
    empty_count = 0
    empty_correct = 0
    forbidden_count = 0
    forbidden_returned = 0
    status_correct = 0
    for row in rows:
        result_ids = row[field][:5]
        expected = set(row["relevant_profile_ids"])
        forbidden = set(row["forbidden_profile_ids"])
        if expected:
            recall = len(expected.intersection(result_ids)) / len(expected)
            recall_sum += recall
            recall_count += 1
            hits += int(recall > 0)
        else:
            recall = None
        is_expected_empty = row["expected_status"] == "empty"
        if is_expected_empty:
            empty_count += 1
            empty_correct += int(not result_ids)
        forbidden_count += len(forbidden)
        forbidden_returned += len(forbidden.intersection(result_ids))
        expected_status = row["expected_status"]
        actual_status = row[status_field or f"{field}_status"]
        status_correct += int(actual_status == expected_status)
        cases.append({"id": row["id"], "recall_at_5": recall, "hit_at_5": bool(expected.intersection(result_ids)) if expected else None,
                      "empty_correct": (not result_ids) if is_expected_empty else None, "status_correct": actual_status == expected_status})
    macro_recall = round(recall_sum / recall_count, 4) if recall_count else None
    specificity = round(1.0 - forbidden_returned / forbidden_count, 4) if forbidden_count else None
    calibration_f1 = (
        round(2 * macro_recall * specificity / (macro_recall + specificity), 4)
        if macro_recall is not None and specificity is not None and macro_recall + specificity > 0
        else 0.0 if macro_recall == 0 or specificity == 0 else None
    )
    return {
        "macro_recall_at_5": macro_recall,
        "hit_at_5": round(hits / recall_count, 4) if recall_count else None,
        "empty_accuracy": round(empty_correct / empty_count, 4) if empty_count else None,
        "forbidden_at_5": forbidden_returned,
        "forbidden_label_count": forbidden_count,
        "specificity_on_forbidden_labels": specificity,
        "calibration_f1": calibration_f1,
        "status_accuracy": round(status_correct / len(rows), 4) if rows else None,
        "cases": cases,
    }


@click.command("search-evaluate")
@click.option("--set", "split", type=click.Choice(("calibration", "evaluation")), required=True)
@with_appcontext
def search_evaluate_command(split):
    """Run the labeled corpus through real Qwen, the semantic encoder, text-only, and common search."""
    require_local_search_database()
    cfg = current_app.config
    if not cfg["AI_SEARCH_ENABLED"]:
        raise click.ClickException("Habilitá AI_SEARCH_ENABLED en backend/.env local antes de medir.")
    if not cfg.get("AI_SEARCH_SEMANTIC_ENABLED", True):
        raise click.ClickException("La evaluación híbrida requiere AI_SEARCH_SEMANTIC_ENABLED=true.")

    backend_dir = Path(__file__).resolve().parents[1]
    dataset_path = backend_dir / "evaluation" / "advanced-search.json"
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes)
    selected = [item for item in dataset["queries"] if item["split"] == split]
    if len(selected) < 12:
        raise click.ClickException(f"El conjunto {split} tiene menos de 12 consultas etiquetadas.")

    from app.models import Profile, ProfileSearchChunk, ProfileSearchDocument
    from app.search.encoder import encode_normalized, get_encoder
    from app.search.llm import InferenceBusy, InferenceUnavailable, authorization_headers, extract_intent
    from app.search.engine import deterministic_intent, prepare_intent, profession_spelling_options, search_profiles
    from app.search.model_manifest import MODEL_DIMENSION, MODEL_NAME, MODEL_REVISION
    from app.api.jobkler import serialize_profile
    from sqlalchemy import distinct

    profiles = db.session.scalars(select(Profile.id).where(Profile.status == "active")).all()
    indexed = set(db.session.scalars(
        select(distinct(ProfileSearchChunk.profile_id))
        .join(ProfileSearchDocument, ProfileSearchDocument.profile_id == ProfileSearchChunk.profile_id)
        .where(
            ProfileSearchChunk.source_hash == ProfileSearchDocument.source_hash,
            ProfileSearchChunk.encoder_model == MODEL_NAME,
            ProfileSearchChunk.encoder_revision == MODEL_REVISION,
            ProfileSearchChunk.vector_dimension == MODEL_DIMENSION,
            ProfileSearchChunk.vector_dtype == "float32-le",
        )
    ).all())
    missing = sorted(set(profiles) - indexed)
    if missing:
        raise click.ClickException(
            f"El corpus no está totalmente indexado ({len(missing)} perfiles activos sin vectores vigentes). "
            "Ejecutá search-rebuild y dejá terminar search-worker antes de evaluar."
        )

    prepare_started = time.perf_counter()
    try:
        encoder = get_encoder(cfg, allow_download=False)
        encode_normalized(encoder, ["Preparación local del encoder para medición."])
    except Exception as exc:
        raise click.ClickException(f"El encoder fijado no está listo: {type(exc).__name__}. Ejecutá search-model-prepare.") from exc
    encoder_warmup_ms = (time.perf_counter() - prepare_started) * 1000

    try:
        with requests.Session() as session:
            session.trust_env = False
            session.headers.update(authorization_headers(cfg["AI_LLM_API_KEY"]))
            response = session.get(f"{cfg['AI_LLM_BASE_URL'].rstrip('/')}/models", timeout=(2, 3))
            response.raise_for_status()
            available_models = [item.get("id") for item in response.json().get("data", []) if isinstance(item, dict)]
    except Exception as exc:
        raise click.ClickException(f"Qwen local no está disponible: {type(exc).__name__}; no se generó una evaluación ficticia.") from exc
    if cfg["AI_LLM_MODEL"] not in available_models:
        raise click.ClickException(
            f"El alias {cfg['AI_LLM_MODEL']} no aparece en /models. Disponibles: {', '.join(str(value) for value in available_models)}"
        )

    output_rows = []
    common_client = current_app.test_client()
    peak_working_set = _process_working_set_bytes()
    qwen_success_count = 0
    calibration_thresholds = (0.45, 0.50, 0.54, 0.58, 0.62, 0.66, 0.70)
    threshold_rows = {threshold: [] for threshold in calibration_thresholds} if split == "calibration" else {}
    for case in selected:
        total_started = time.perf_counter()
        parse_started = time.perf_counter()
        qwen_state = "ok"
        try:
            intent = extract_intent(
                case["query"], base_url=cfg["AI_LLM_BASE_URL"], model=cfg["AI_LLM_MODEL"],
                api_key=cfg["AI_LLM_API_KEY"],
                timeout_seconds=cfg["AI_SEARCH_TIMEOUT_SECONDS"],
                connect_timeout_seconds=cfg["AI_SEARCH_CONNECT_TIMEOUT_SECONDS"],
                queue_wait_seconds=cfg["AI_SEARCH_QUEUE_WAIT_SECONDS"],
            )
            qwen_success_count += 1
        except InferenceBusy as exc:
            raise click.ClickException(f"Qwen estaba ocupado en {case['id']}; evaluación detenida, sin reintentos.") from exc
        except InferenceUnavailable as exc:
            qwen_state = f"degraded:{type(exc).__name__}"
            intent = deterministic_intent(case["query"])
        parse_ms = (time.perf_counter() - parse_started) * 1000

        prepare_intent(intent, case["query"])
        special_status = None
        if intent.status in {"ambiguous", "unsupported"}:
            special_status = intent.status
        elif not intent.profession_text and profession_spelling_options(case["query"]):
            special_status = "ambiguous"

        query_embedding_ms = 0.0
        query_vector = None
        if not special_status:
            embedding_started = time.perf_counter()
            query_vector = encode_normalized(
                encoder, [" ".join(value for value in (intent.search_text, *intent.related_terms) if value)]
            )[0]
            query_embedding_ms = (time.perf_counter() - embedding_started) * 1000

        if special_status:
            hybrid = {"status": special_status, "results": [], "metrics": {}}
            text_only = {"status": special_status, "results": [], "metrics": {}}
            hybrid_wall_ms = text_wall_ms = 0.0
        else:
            hybrid_started = time.perf_counter()
            hybrid = search_profiles(
                intent, query=case["query"], limit=5, config=cfg, encoder=encoder, query_vector=query_vector,
                serialize_profile=serialize_profile, include_metrics=True,
            )
            hybrid_wall_ms = (time.perf_counter() - hybrid_started) * 1000

            text_config = dict(cfg)
            text_config["AI_SEARCH_SEMANTIC_ENABLED"] = False
            text_started = time.perf_counter()
            text_only = search_profiles(
                intent, query=case["query"], limit=5, config=text_config,
                serialize_profile=serialize_profile, include_metrics=True,
            )
            text_wall_ms = (time.perf_counter() - text_started) * 1000

        common_started = time.perf_counter()
        common_response = common_client.get("/api/profiles", query_string={"q": case["query"], "limit": 5})
        if common_response.status_code != 200:
            raise click.ClickException(f"La búsqueda común devolvió HTTP {common_response.status_code} para {case['id']}.")
        common_items = common_response.get_json().get("items", [])
        common_ms = (time.perf_counter() - common_started) * 1000

        hybrid_ids = [item["profile"]["id"] for item in hybrid["results"][:5]]
        text_ids = [item["profile"]["id"] for item in text_only["results"][:5]]
        common_ids = [item["id"] for item in common_items[:5]]
        comparison_total_ms = (time.perf_counter() - total_started) * 1000
        for expected in case["relevant_profile_ids"]:
            if db.session.get(Profile, expected) is None:
                raise click.ClickException(f"La etiqueta {case['id']} referencia un perfil ausente: {expected}.")
        if split == "calibration":
            for threshold in calibration_thresholds:
                if special_status:
                    threshold_result = {"status": special_status, "results": []}
                elif abs(threshold - float(cfg["AI_SEARCH_SEMANTIC_MIN_COSINE"])) < 1e-9:
                    threshold_result = hybrid
                else:
                    candidate_config = dict(cfg)
                    candidate_config["AI_SEARCH_SEMANTIC_MIN_COSINE"] = threshold
                    threshold_result = search_profiles(
                        intent, query=case["query"], limit=5, config=candidate_config,
                        encoder=encoder, query_vector=query_vector, serialize_profile=serialize_profile,
                    )
                threshold_rows[threshold].append({
                    "id": case["id"], "expected_status": case["expected_status"],
                    "relevant_profile_ids": case["relevant_profile_ids"],
                    "forbidden_profile_ids": case["forbidden_profile_ids"],
                    "result_ids": [item["profile"]["id"] for item in threshold_result["results"][:5]],
                    "result_status": threshold_result["status"],
                })
        output_rows.append({
            "id": case["id"], "query": case["query"], "expected_status": case["expected_status"],
            "relevant_profile_ids": case["relevant_profile_ids"], "forbidden_profile_ids": case["forbidden_profile_ids"],
            "hybrid": hybrid_ids, "hybrid_status": hybrid["status"],
            "text_only": text_ids, "text_only_status": text_only["status"],
            "common": common_ids, "common_status": "ok" if common_ids else "empty",
            "qwen_state": qwen_state,
            "latency_ms": {"qwen_parse": parse_ms, "hybrid_total": hybrid_wall_ms,
                           "text_only_total": text_wall_ms, "common": common_ms,
                           "qwen_plus_hybrid": parse_ms + query_embedding_ms + hybrid_wall_ms,
                           "evaluation_comparison_total": comparison_total_ms,
                           **{**hybrid.get("metrics", {}), "query_embedding_ms": query_embedding_ms}},
        })
        memory_now = _process_working_set_bytes()
        if memory_now is not None:
            peak_working_set = max(peak_working_set or 0, memory_now)

    metric_names = ("qwen_parse", "filter_ms", "fts_ms", "query_embedding_ms", "vector_scan_ms", "retrieval_ms",
                    "hybrid_total", "text_only_total", "common", "qwen_plus_hybrid", "evaluation_comparison_total")
    threshold_sweep = {
        str(threshold): _retrieval_metrics(rows, field="result_ids", status_field="result_status")
        for threshold, rows in threshold_rows.items()
    }
    recommended_threshold = None
    if threshold_sweep:
        recommended_threshold = min(
            calibration_thresholds,
            key=lambda threshold: (
                -(threshold_sweep[str(threshold)]["calibration_f1"] or 0.0),
                -(threshold_sweep[str(threshold)]["empty_accuracy"] or 0.0),
                -(threshold_sweep[str(threshold)]["macro_recall_at_5"] or 0.0),
                threshold_sweep[str(threshold)]["forbidden_at_5"],
                abs(threshold - float(cfg["AI_SEARCH_SEMANTIC_MIN_COSINE"])),
            ),
        )
    result = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "split": split,
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "conditions": {
            "machine": platform.node(), "os": platform.platform(), "cpu": platform.processor() or None,
            "logical_cpu_count": os.cpu_count(), "python": sys.version.split()[0],
            "qwen_base_url": cfg["AI_LLM_BASE_URL"], "qwen_model": cfg["AI_LLM_MODEL"],
            "qwen_completion_successes": qwen_success_count, "qwen_post_attempts": len(output_rows), "qwen_model_list_checks": 1,
            "encoder_name": cfg["AI_SEARCH_ENCODER_MODEL"], "encoder_revision": cfg["AI_SEARCH_ENCODER_REVISION"],
            "fastembed_threads": cfg["AI_SEARCH_EMBEDDING_THREADS"], "semantic_threshold": cfg["AI_SEARCH_SEMANTIC_MIN_COSINE"],
            "cache_state": "encoder preloaded/warm; llama.cpp process and OS page cache state not controlled",
            "encoder_warmup_ms": round(encoder_warmup_ms, 2),
            "max_cli_working_set_bytes": peak_working_set,
            "active_profiles": len(profiles), "profiles_with_current_vectors": len(indexed),
        },
        "metrics": {
            "hybrid": _retrieval_metrics(output_rows, field="hybrid"),
            "text_only": _retrieval_metrics(output_rows, field="text_only"),
            "common": _retrieval_metrics(output_rows, field="common"),
            "latency": {
                name: _metric_summary([row["latency_ms"].get(name) for row in output_rows])
                for name in metric_names
            },
        },
        "calibration": {
            "threshold_sweep": threshold_sweep,
            "recommended_threshold": recommended_threshold,
            "recommendation_rule": "maximizar la media armónica entre Recall@5 macro y especificidad sobre etiquetas prohibidas; desempatar por acierto en consultas vacías, recall y cercanía al umbral configurado; no modifica backend/.env",
        } if split == "calibration" else None,
        "queries": output_rows,
    }
    output_dir = INSTANCE_DIR / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"advanced-search-{split}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    click.echo(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    click.echo(f"Informe de medición guardado en: {output_path}")


def register_commands(app):
    app.cli.add_command(seed_jobkler_command)
    app.cli.add_command(reset_demo_command)
    for command in (
        seed_search_fixtures_command,
        seed_expanded_profiles_command,
        search_rebuild_command,
        search_model_prepare_command,
        search_model_check_command,
        search_index_once_command,
        search_index_status_command,
        search_check_llm_command,
        search_worker_command,
        search_evaluate_command,
    ):
        app.cli.add_command(command)

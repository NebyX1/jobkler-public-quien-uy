"""Live, labeled evaluation of the related-results search flow."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import func, select

from app.extensions import db
from app.models import Profile, ProfileSearchChunk, ProfileSearchDocument
from app.search.catalog import eligible_profile_ids, resolve_filters
from app.search.contracts import AdvancedSearchRequest
from app.search.documents import SEARCH_FIELDS, hash_search_fields, profile_search_fields
from app.search.model_manifest import MODEL_DIMENSION, MODEL_NAME, MODEL_REVISION
from app.search.text import contains_number_variant, normalize_text


DATASET = Path(__file__).resolve().parents[2] / "evaluation" / "reranker-search.json"
TOP_K = 3
RESERVED_SPLITS = ("heldout", "fresh")


def _audit_target_absence(case, payload):
    terms = list(dict.fromkeys(normalize_text(term) for term in case["absent_target_terms"]))
    if (not terms or "" in terms
            or not any(contains_number_variant(payload.query, term) for term in terms)):
        raise click.ClickException(f"El caso {case['id']} requiere términos objetivo concretos.")
    if payload.locationScope == "national":
        geo = {"department": None, "locality": None, "source": "national"}
    else:
        filters = case.get("filters", {})
        geo, clarification = resolve_filters(
            payload.query, None,
            filters.get("departmentId", payload.departmentId),
            filters.get("localityId", payload.localityId),
        )
        if clarification:
            raise click.ClickException(f"No se pudo auditar el alcance de {case['id']}: {clarification['code']}.")

    eligible = eligible_profile_ids(geo)
    indexed = db.session.execute(
        select(Profile, ProfileSearchDocument)
        .outerjoin(ProfileSearchDocument, ProfileSearchDocument.profile_id == Profile.id)
        .where(Profile.id.in_(eligible))
        .order_by(Profile.id)
    ).all()
    outdated = []
    hits = []
    for profile, document in indexed:
        if not document:
            outdated.append(profile.id)
            continue
        fields = {field: getattr(document, field) for field in SEARCH_FIELDS}
        if (document.source_hash != hash_search_fields(fields)
                or document.source_hash != hash_search_fields(profile_search_fields(profile))):
            outdated.append(profile.id)
        for field, value in fields.items():
            for term in terms:
                if contains_number_variant(value, term):
                    hits.append({"profile_id": profile.id, "field": field, "term": term})

    ineligible_labels = sorted(set(case.get("relevant", [])) - eligible)
    eligible_forbidden = sorted(set(case.get("forbidden", [])) & eligible)
    missing_negative_control = (
        case.get("split") in RESERVED_SPLITS and case["expected"] == "empty" and not eligible_forbidden
    )
    return {
        "target_terms": terms,
        "scope": {
            "departmentId": geo["department"].id if geo["department"] else None,
            "localityId": geo["locality"].id if geo["locality"] else None,
        },
        "eligible_profiles": len(eligible),
        "indexed_profiles": len(eligible) - len(outdated),
        "hits": hits,
        "outdated_index_profile_ids": outdated,
        "ineligible_relevant_profile_ids": ineligible_labels,
        "eligible_forbidden_profile_ids": eligible_forbidden,
        "missing_negative_control": missing_negative_control,
        "passed": not (hits or outdated or ineligible_labels or missing_negative_control),
    }


def _audit_selected_cases(cases, payloads):
    reports = {}
    for case in cases:
        case_id = case["id"]
        if case.get("split") in RESERVED_SPLITS and not (
            case.get("absent_target_terms") and case["expected"] in {"related", "empty"}
            and (case["expected"] == "empty" or (case.get("relevant") and case.get("relationship")))
        ):
            raise click.ClickException(f"El caso reservado {case_id} requiere términos ausentes y una expectativa verificable.")
        if "absent_target_terms" not in case:
            continue
        audit = _audit_target_absence(case, payloads[case_id])
        reports[case_id] = audit
        marker = "OK" if audit["passed"] else "REVISAR"
        click.echo(f"{marker} corpus {case_id}: {audit['indexed_profiles']}/{audit['eligible_profiles']} perfiles vigentes, "
                   f"{len(audit['hits'])} menciones del objetivo")
        if not audit["passed"]:
            click.echo(json.dumps(audit, ensure_ascii=False), err=True)
    if any(not report["passed"] for report in reports.values()):
        raise click.ClickException("Falló la auditoría del corpus. No se ejecutaron inferencias de evaluación.")
    return reports


def _require_current_index():
    indexed = (
        select(ProfileSearchChunk.profile_id)
        .join(ProfileSearchDocument, ProfileSearchDocument.profile_id == ProfileSearchChunk.profile_id)
        .where(
            ProfileSearchChunk.source_hash == ProfileSearchDocument.source_hash,
            ProfileSearchChunk.encoder_model == MODEL_NAME,
            ProfileSearchChunk.encoder_revision == MODEL_REVISION,
            ProfileSearchChunk.vector_dimension == MODEL_DIMENSION,
            ProfileSearchChunk.vector_dtype == "float32-le",
        )
    )
    missing = db.session.scalar(
        select(func.count()).select_from(Profile)
        .where(Profile.status == "active", ~Profile.id.in_(indexed))
    )
    if missing:
        raise click.ClickException(
            f"El corpus tiene {missing} perfiles activos sin vectores vigentes. "
            "Ejecutá search-rebuild y dejá terminar search-worker."
        )


def _run_case(payload):
    from app.api.advanced_search import _search_events

    started = perf_counter()
    stage = None
    stage_started = started
    phase_ms = {}
    for event in _search_events(payload):
        now = perf_counter()
        if stage is not None:
            phase_ms[stage] = round((now - stage_started) * 1000, 2)
        if event["type"] == "result":
            phase_ms["total"] = round((now - started) * 1000, 2)
            return event["status"], event["result"], phase_ms
        stage = event["stage"]
        stage_started = now
    raise RuntimeError("La búsqueda terminó sin entregar un resultado.")


def _grade(case, http_status, result, phase_ms, corpus_audit=None):
    expected = case["expected"]
    results = [
        {"id": item["profile"]["id"], "match_type": item["evidence"]["matchType"]}
        for item in result["results"]
    ]
    suggestion_evidence = [
        {"id": item["profile"]["id"], "text": item["evidence"]["text"], "source_field": item["evidence"]["sourceField"]}
        for item in result.get("suggestions", [])
    ]
    suggestions = [item["id"] for item in suggestion_evidence]
    result_ids = [item["id"] for item in results]
    degraded = result["status"] == "degraded" or bool(result.get("degradation"))
    if http_status >= 400:
        outcome = "unavailable"
    elif result["status"] == "ambiguous":
        outcome = "clarify"
    elif any(item["match_type"] == "direct" for item in results):
        outcome = "direct"
    elif suggestions:
        outcome = "related"
    elif results:
        outcome = "legacy_related"
    else:
        outcome = "empty"

    relevant = set(case.get("relevant", []))
    forbidden = set(case.get("forbidden", []))
    top = (
        [item["id"] for item in results[:TOP_K] if item["match_type"] == "direct"]
        if expected == "direct" else suggestions[:TOP_K]
    )
    hits = len(relevant.intersection(top))
    forbidden_hits = sorted(forbidden.intersection(result_ids + suggestions))
    outside_labels = sorted(set(top) - relevant - forbidden)
    expected_filters = case.get("filters", {})
    filters = result.get("applied_filters") or {}
    scope_correct = all(filters.get(key) == value for key, value in expected_filters.items())
    clarification = result.get("clarification") or {}
    option_ids = {option["id"] for option in clarification.get("options", []) if option.get("id")}
    options_correct = set(case.get("clarification_options", [])).issubset(option_ids)
    if expected in {"empty", "clarify"}:
        content_correct = not (result_ids or suggestions)
    else:
        content_correct = bool(hits)
    if "absent_target_terms" in case:
        content_correct = content_correct and bool(corpus_audit and corpus_audit["passed"])
    if case.get("split") in RESERVED_SPLITS:
        content_correct = content_correct and not outside_labels
    return {
        "id": case["id"],
        "split": case.get("split", "regression"),
        "input": case["input"],
        "relationship": case.get("relationship"),
        "corpus_audit": corpus_audit,
        "expected": expected,
        "actual": outcome,
        "status": result["status"],
        "http_status": http_status,
        "passed": (
            outcome == expected and content_correct and scope_correct and options_correct
            and not forbidden_hits and not degraded
        ),
        "scope_correct": scope_correct,
        "filters": filters,
        "clarification_code": clarification.get("code"),
        "clarification_option_ids": sorted(option_ids),
        "clarification_options_correct": options_correct,
        "results": results,
        "suggestions": suggestions,
        "suggestion_evidence": suggestion_evidence,
        "relevant_at_3": hits,
        "judged_at_3": hits + len(forbidden.intersection(top)),
        "unjudged_at_3": outside_labels if relevant else [],
        "forbidden_returned": forbidden_hits,
        "degraded": degraded,
        "latency_ms": phase_ms,
    }


def _summary(rows, summarize_latency):
    metrics = {}
    for group in ("direct", "related", "empty", "clarify"):
        cases = [row for row in rows if row["expected"] == group]
        judged = sum(row["judged_at_3"] for row in cases)
        relevant = sum(row["relevant_at_3"] for row in cases)
        group_metrics = {"cases": len(cases), "passed": sum(row["passed"] for row in cases)}
        if group in {"direct", "related"}:
            group_metrics.update(
                hit_rate_at_3=round(sum(bool(row["relevant_at_3"]) for row in cases) / len(cases), 4) if cases else None,
                judged_precision_at_3=round(relevant / judged, 4) if judged else None,
                unjudged_at_3=sum(len(row["unjudged_at_3"]) for row in cases),
            )
        metrics[group] = group_metrics
    return {
        "cases": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "degraded": sum(row["degraded"] for row in rows),
        "forbidden_returned": sum(len(row["forbidden_returned"]) for row in rows),
        "groups": metrics,
        "splits": {
            split: {"cases": len(cases), "passed": sum(row["passed"] for row in cases)}
            for split in ("regression", *RESERVED_SPLITS)
            if (cases := [row for row in rows if row["split"] == split])
        },
        "target_absent": {
            "cases": sum(row["corpus_audit"] is not None for row in rows),
            "passed": sum(row["passed"] and row["corpus_audit"] is not None for row in rows),
        },
        "latency_ms": {
            stage: summarize_latency([row["latency_ms"].get(stage) for row in rows])
            for stage in ("total", "interpretation", "location", "retrieval")
        },
    }


@click.command("search-evaluate-related")
@click.option("--split", type=click.Choice(("all", "regression", *RESERVED_SPLITS)), default="all", show_default=True)
@click.option("--case", "case_ids", multiple=True, help="Ejecutá una consulta por ID. Se puede repetir.")
@click.option("--limit", type=click.IntRange(min=1), help="Cantidad máxima de consultas.")
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path), help="Ruta nueva para el informe JSON.")
@click.option("--strict", is_flag=True, help="Terminá con error si algún caso falla.")
@click.option("--check-corpus", is_flag=True, help="Audita el corpus de los casos seleccionados sin ejecutar modelos.")
@with_appcontext
def quality_evaluate_command(split, case_ids, limit, output, strict, check_corpus):
    """Medí la búsqueda avanzada con Qwen, MiniLM y el reranker locales."""
    from app.commands import _metric_summary, require_local_search_database
    from app.search.encoder import encode_normalized, get_encoder
    from app.search.reranker import rerank_scores

    require_local_search_database()
    config = current_app.config
    dataset_bytes = DATASET.read_bytes()
    cases = json.loads(dataset_bytes)["queries"]
    if split != "all":
        cases = [case for case in cases if case.get("split", "regression") == split]
    if case_ids:
        by_id = {case["id"]: case for case in cases}
        unknown = sorted(set(case_ids) - by_id.keys())
        if unknown:
            raise click.ClickException("IDs de consulta sin etiqueta: " + ", ".join(unknown))
        cases = [by_id[case_id] for case_id in dict.fromkeys(case_ids)]
    cases = cases[:limit]
    payloads = {case["id"]: AdvancedSearchRequest.model_validate(case["input"]) for case in cases}
    corpus_audits = _audit_selected_cases(cases, payloads)
    if check_corpus:
        click.echo(f"{len(corpus_audits)} casos con ausencia del objetivo comprobada.")
        return

    if not config["AI_SEARCH_ENABLED"] or not config["AI_SEARCH_SEMANTIC_ENABLED"] or not config["AI_SEARCH_RERANKER_ENABLED"]:
        raise click.ClickException("Habilitá la búsqueda avanzada, el encoder semántico y el reranker local.")

    started_at = datetime.now(timezone.utc)
    report_path = output or (
        Path(current_app.instance_path) / "evaluation" / f"related-{started_at:%Y%m%dT%H%M%S%fZ}.json"
    )
    if report_path.exists():
        raise click.ClickException(f"Ya existe el archivo {report_path}. Elegí otra ruta.")

    _require_current_index()
    labeled_ids = {profile_id for case in cases for profile_id in case.get("relevant", [])}
    present = set(db.session.scalars(select(Profile.id).where(Profile.id.in_(labeled_ids))))
    missing = sorted(labeled_ids - present)
    if missing:
        click.echo(f"Advertencia: faltan {len(missing)} perfiles etiquetados en esta base. Revisá las semillas locales.", err=True)

    warmup_started = perf_counter()
    try:
        encode_normalized(get_encoder(config), ["Reparación de muebles"])
        rerank_scores("Reparación de muebles", ["Reparo muebles de madera"], config)
    except Exception as exc:
        raise click.ClickException(
            f"Los modelos ONNX locales no quedaron listos ({type(exc).__name__}). "
            "Prepará el encoder y el reranker antes de evaluar."
        ) from exc
    warmup_ms = round((perf_counter() - warmup_started) * 1000, 2)

    rows = []
    for case in cases:
        row = _grade(case, *_run_case(payloads[case["id"]]), corpus_audit=corpus_audits.get(case["id"]))
        rows.append(row)
        marker = "OK" if row["passed"] else "REVISAR"
        click.echo(f"{marker} {row['id']}: {row['actual']} ({row['latency_ms']['total'] / 1000:.2f} s)")

    metrics = _summary(rows, _metric_summary)
    report = {
        "schema_version": 2,
        "created_at": started_at.isoformat(),
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "model_warmup_ms": warmup_ms,
        "missing_labeled_profile_ids": missing,
        "metrics": metrics,
        "cases": rows,
    }
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("x", encoding="utf-8") as output_file:
            json.dump(report, output_file, ensure_ascii=False, indent=2)
            output_file.write("\n")
    except OSError as exc:
        raise click.ClickException(f"No se pudo guardar el informe en {report_path}: {exc.strerror}.") from exc
    click.echo(f"{metrics['passed']}/{metrics['cases']} casos cumplieron la expectativa. Informe: {report_path.resolve()}")
    if strict and metrics["passed"] != metrics["cases"]:
        raise click.ClickException("Hay consultas que requieren revisión. El informe contiene el detalle.")

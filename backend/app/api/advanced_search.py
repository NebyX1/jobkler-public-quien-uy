import json
from time import perf_counter
from uuid import uuid4

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.extensions import db
from app.services.sessions import require_csrf, current_account

from .jobkler import serialize_profile, api_error
from app.search.catalog import eligible_profile_ids, resolve_filters
from app.search.contracts import AdvancedSearchRequest
from app.search.engine import (
    deterministic_intent, explicit_profession_intent, prepare_intent, profession_spelling_options,
    reserve_account_request, search_profiles,
)
from app.search.llm import (
    InferenceBusy, InferenceUnavailable, extract_intent, propose_related_services, verify_related_evidence,
)
from app.search.related import publish_suggestions, related_candidates

advanced_search_bp = Blueprint("advanced_search_api", __name__, url_prefix="/search")
PROGRESS_TYPE = "application/x-ndjson"


def _response(status, message, *, code=None):
    result = {"request_id": uuid4().hex, "status": status, "message": message, "results": []}
    if code:
        result["error"] = {"code": code, "message": message}
    return result


def _result(result, status=200):
    return {"type": "result", "status": status, "result": result}


@advanced_search_bp.post("/advanced")
def advanced_search():
    account = current_account()
    if not account:
        return api_error("Iniciá sesión para usar la búsqueda avanzada.", 401)
    if not require_csrf():
        return api_error("Token CSRF inválido o vencido.", 403)
    if not current_app.config["AI_SEARCH_ENABLED"]:
        return _response("error", "La búsqueda avanzada no está habilitada en este entorno.", code="disabled"), 503

    try:
        raw_payload = request.get_json(silent=True)
        if isinstance(raw_payload, dict) and "limit" not in raw_payload:
            raw_payload["limit"] = current_app.config["AI_SEARCH_DEFAULT_RESULTS"]
        payload = AdvancedSearchRequest.model_validate(raw_payload)
    except ValidationError as exc:
        return jsonify({"error": "La búsqueda tiene campos inválidos.", "details": exc.errors(include_input=False, include_context=False)}), 400
    except (TypeError, ValueError):
        return api_error("La solicitud debe ser un objeto JSON válido.", 400)
    if len(payload.query) > current_app.config["AI_SEARCH_MAX_QUERY_CHARS"]:
        return api_error("La búsqueda supera el límite configurado de caracteres.", 400)

    try:
        if not reserve_account_request(account.id, current_app.config["AI_SEARCH_RATE_LIMIT_PER_HOUR"]):
            return _response("busy", "Alcanzaste el límite temporal de búsquedas avanzadas.", code="rate_limited"), 429
    except OperationalError:
        db.session.rollback()
        return _response("busy", "La búsqueda está ocupada. Probá nuevamente en un momento.", code="database_busy"), 503

    events = _search_events(payload)
    if request.accept_mimetypes.best == PROGRESS_TYPE:
        return Response(
            stream_with_context(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
            content_type=PROGRESS_TYPE,
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no", "Vary": "Accept"},
        )

    for event in events:
        if event["type"] == "result":
            return jsonify(event["result"]), event["status"], {"Vary": "Accept"}


def _search_events(payload):
    yield {"type": "stage", "stage": "interpretation"}
    degradation = []
    try:
        intent = explicit_profession_intent(payload.query)
        if intent is None:
            intent = extract_intent(
                payload.query,
                base_url=current_app.config["AI_LLM_BASE_URL"],
                model=current_app.config["AI_LLM_MODEL"],
                api_key=current_app.config["AI_LLM_API_KEY"],
                timeout_seconds=current_app.config["AI_SEARCH_TIMEOUT_SECONDS"],
                connect_timeout_seconds=current_app.config["AI_SEARCH_CONNECT_TIMEOUT_SECONDS"],
                queue_wait_seconds=current_app.config["AI_SEARCH_QUEUE_WAIT_SECONDS"],
            )
    except InferenceBusy:
        yield _result(_response("busy", "El motor local está ocupado; esperá un momento y reenviá la búsqueda.", code="inference_busy"), 503)
        return
    except InferenceUnavailable as exc:
        intent = deterministic_intent(payload.query)
        degradation.append(f"No se pudo interpretar con Qwen local ({str(exc)}); se aplicó extracción determinista.")

    if intent.status == "ambiguous":
        result = _response("ambiguous", "La consulta permite más de una interpretación. Editá el texto y volvé a buscar.")
        result.update(applied_filters={}, clarification={"code": "service_ambiguous", "options": []})
        yield _result(result)
        return
    if intent.status == "unsupported":
        yield _result({**_response("unsupported", "Escribí un servicio u oficio para buscar perfiles."), "applied_filters": {}})
        return

    yield {"type": "stage", "stage": "location"}
    # Keep geographic tokens out of service retrieval; the catalog filter is applied separately.
    prepare_intent(intent, payload.query)

    if not intent.profession_text:
        profession_options = profession_spelling_options(payload.query)
        if profession_options:
            result = _response("ambiguous", profession_options["message"])
            result.update(applied_filters={}, clarification=profession_options)
            yield _result(result)
            return

    geography = (
        ({"department": None, "locality": None, "source": "national"}, None)
        if payload.locationScope == "national"
        else resolve_filters(payload.query, intent.location_text, payload.departmentId, payload.localityId)
    )
    if not geography[1]:
        yield {"type": "stage", "stage": "retrieval"}

    result = search_profiles(
        intent,
        query=payload.query,
        resolved_geography=geography,
        limit=min(payload.limit, current_app.config["AI_SEARCH_MAX_RESULTS"]),
        config=current_app.config,
        serialize_profile=serialize_profile,
    )
    if (not degradation and result["status"] in {"ok", "empty"} and not geography[1]
            and current_app.config["AI_SEARCH_RERANKER_ENABLED"]
            and current_app.config["AI_SEARCH_SEMANTIC_ENABLED"]):
        direct = [match for match in result["results"] if match["evidence"]["matchType"] == "direct"]
        if direct:
            result["results"] = direct
        else:
            _search_related(result, intent, payload, geography[0])
    if degradation and result["status"] in {"ok", "empty"}:
        result["status"] = "degraded"
        result["degradation"] = degradation + result.get("degradation", [])
        result["message"] += " La interpretación local no respondió y se usó una búsqueda determinista."
    yield _result(result)


def _search_related(result, intent, payload, geo):
    started = perf_counter()
    config = current_app.config
    connection = {
        "base_url": config["AI_LLM_BASE_URL"], "model": config["AI_LLM_MODEL"],
        "api_key": config["AI_LLM_API_KEY"],
        "connect_timeout_seconds": config["AI_SEARCH_CONNECT_TIMEOUT_SECONDS"],
        "queue_wait_seconds": config["AI_SEARCH_QUEUE_WAIT_SECONDS"],
    }
    stage = "retrieval"
    try:
        candidates = related_candidates(intent, query=payload.query, geo=geo, config=config)
        if (not candidates and (intent.action_text or intent.object_text or not intent.profession_text)
                and eligible_profile_ids(geo, intent.profession_text)):
            stage = "service_plan"
            services = propose_related_services(payload.query, **connection)
            if services:
                expanded = intent.model_copy(update={"related_services": services})
                stage = "expanded_retrieval"
                candidates = related_candidates(
                    expanded, query=payload.query, geo=geo, config=config, allow_semantic=True,
                )
        if candidates:
            stage = "verification"
            accepted = verify_related_evidence(
                payload.query, [candidate.verification_text for candidate in candidates], **connection,
            )
            suggestions = publish_suggestions(
                candidates, accepted, intent=intent, geo=geo, serialize_profile=serialize_profile,
                limit=min(payload.limit, config["AI_SEARCH_MAX_RESULTS"]),
            )
            if suggestions:
                result.update(
                    status="ok", results=[], suggestions=suggestions,
                    message="No encontré una coincidencia exacta. Estos perfiles podrían ayudarte.",
                )
                return
        result.update(status="empty", results=[], message="No encontré coincidencias suficientes entre los perfiles activos.")
    except Exception as exc:
        current_app.logger.warning(
            "advanced_search_related_failed request_id=%s stage=%s error=%s cause=%s",
            result["request_id"], stage, type(exc).__name__, type(exc.__cause__ or exc).__name__,
        )
        result.update(
            status="degraded", results=[],
            message="La verificación de sugerencias relacionadas no está disponible.",
        )
        result["degradation"].append(result["message"])
    finally:
        current_app.logger.info(
            "advanced_search_related request_id=%s suggestions=%d total_ms=%.1f",
            result["request_id"], len(result.get("suggestions", [])), (perf_counter() - started) * 1000,
        )

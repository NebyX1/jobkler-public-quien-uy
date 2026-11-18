import logging
import re
import time
import uuid
from difflib import SequenceMatcher

import numpy as np
from sqlalchemy import bindparam, select, text

from app.extensions import db
from app.models import (
    AdvancedSearchRateEvent,
    Department,
    Locality,
    Profile,
    ProfileCoverage,
    ProfileSearchChunk,
    ProfileSearchDocument,
)
from app.models.jobkler import utcnow

from . import aliases
from .catalog import detect_location_mentions, eligible_profile_ids, fuzzy_location_suggestions, resolve_filters
from .contracts import SearchIntent
from .documents import hash_search_fields, profile_search_fields
from .encoder import encode_normalized, get_encoder
from .model_manifest import MODEL_DIMENSION, MODEL_NAME, MODEL_REVISION
from .text import contains_phrase, normalize_text, tokens, unique_terms

logger = logging.getLogger(__name__)
RRF_CONSTANT = 60
LEXICAL_POOL_SIZE = 200
SEMANTIC_SCORE_LIMIT = 120


def _remove_known_places(query):
    text_value = query
    for model in (Department, Locality):
        rows = db.session.scalars(select(model)).all()
        for row in sorted(rows, key=lambda item: len(item.name), reverse=True):
            text_value = re.sub(re.escape(row.name), " ", text_value, flags=re.IGNORECASE)
    return text_value


def _fallback_location(query):
    departments, localities = detect_location_mentions(query)
    if len(localities) == 1:
        return localities[0].name
    if len(departments) == 1:
        return departments[0].name
    match = re.search(r"\ben\s+([^,.?!;]+)", query, flags=re.IGNORECASE)
    if match:
        words = match.group(1).strip().split()
        for length in range(min(3, len(words)), 0, -1):
            candidate = " ".join(words[:length])
            options = fuzzy_location_suggestions(candidate, limit=1)
            if options:
                return candidate
    return None


def deterministic_intent(query):
    profession_text = None
    for group in aliases.PROFESSION_GROUPS.values():
        for alias in group:
            if contains_phrase(query, alias):
                profession_text = next(key for key, value in aliases.PROFESSION_GROUPS.items() if value is group)
                break
        if profession_text:
            break
    action_text = None
    action_canonical = None
    for canonical, group in aliases.ACTION_GROUPS.items():
        match = next((item for item in group if contains_phrase(query, item)), None)
        if match:
            action_text = match
            action_canonical = canonical
            break
    object_text = None
    related_terms = []
    for canonical, group in aliases.OBJECT_GROUPS.items():
        match = next((item for item in group if contains_phrase(query, item)), None)
        if match:
            object_text = match
            related_terms = [item for item in group if normalize_text(item) != normalize_text(match)][:4]
            break
    location_text = _fallback_location(query)
    cleaned = _remove_known_places(query)
    surviving = [word for word in tokens(cleaned) if word not in aliases.SPANISH_STOP_WORDS]
    search_text = " ".join(surviving)[:300] or " ".join(tokens(query))[:300]
    return SearchIntent(
        status="ok", search_text=search_text,
        profession_text=profession_text, action_text=action_text,
        object_text=object_text, location_text=location_text,
        related_terms=related_terms, excluded_terms=[],
    )


def prepare_intent(intent, query):
    """Apply catalog-based location removal shared by the HTTP route and evaluation CLI."""
    if not intent.location_text:
        intent.location_text = _fallback_location(query)
    departments, localities = __import__("app.search.catalog", fromlist=["detect_location_mentions"]).detect_location_mentions(query)
    geo_words = {
        word
        for row in [*departments, *localities]
        for word in normalize_text(row.name).split()
    }
    intent.search_text = " ".join(word for word in normalize_text(intent.search_text).split() if word not in geo_words)
    if intent.status == "ok" and not intent.search_text:
        intent.search_text = deterministic_intent(query).search_text
    return intent


def reserve_account_request(account_id, limit_per_hour):
    """A short SQLite write transaction makes the account limit shared across API threads."""
    now = utcnow()
    from datetime import timedelta
    cutoff = now - timedelta(hours=1)
    with db.engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        connection.execute(text(
            "DELETE FROM advanced_search_rate_events WHERE account_id=:account_id AND created_at < :cutoff"
        ), {"account_id": account_id, "cutoff": cutoff})
        count = connection.execute(text(
            "SELECT count(*) FROM advanced_search_rate_events WHERE account_id=:account_id AND created_at >= :cutoff"
        ), {"account_id": account_id, "cutoff": cutoff}).scalar_one()
        if count >= limit_per_hour:
            connection.rollback()
            return False
        connection.execute(text(
            "INSERT INTO advanced_search_rate_events (account_id, created_at) VALUES (:account_id, :now)"
        ), {"account_id": account_id, "now": now})
        connection.commit()
    return True


def _profession_resolution(profession_text):
    if not profession_text:
        return None, None
    target = normalize_text(profession_text)
    group = next((items for name, items in aliases.PROFESSION_GROUPS.items() if target == normalize_text(name) or target in {normalize_text(item) for item in items}), None)
    accepted = {normalize_text(value) for value in (group or (profession_text,))}
    available = db.session.execute(select(Profile.profession, Profile.profession_normalized).where(Profile.status == "active").distinct()).all()
    present = {normalized for _label, normalized in available}
    if accepted & present:
        return accepted, None
    if group:
        # A recognized profession may have no current profiles; zero is the honest answer.
        return accepted, None
    choices = []
    for label, normalized in available:
        similarity = SequenceMatcher(None, target, normalize_text(label)).ratio()
        if similarity >= 0.78:
            choices.append((similarity, label))
    choices.sort(key=lambda row: (-row[0], row[1]))
    if choices:
        return None, {
            "code": "profession_spelling",
            "message": "No pude confirmar ese oficio. Elegí una coincidencia del catálogo o quitá el filtro.",
            "options": [{"kind": "profession", "name": label} for _, label in choices[:5]],
        }
    return accepted, None


def profession_spelling_options(query):
    """Offer a catalog correction for a likely typo; never silently select it."""
    available = db.session.execute(select(Profile.profession).where(Profile.status == "active").distinct()).scalars().all()
    known = {normalize_text(value) for value in available}
    reserved = {
        word
        for group in (*aliases.ACTION_GROUPS.values(), *aliases.OBJECT_GROUPS.values(), *aliases.PROFESSION_GROUPS.values())
        for phrase in group
        for word in tokens(phrase)
    }
    candidates = []
    for word in tokens(query):
        if len(word) < 5 or word in reserved or word in known:
            continue
        matches = sorted(
            ((SequenceMatcher(None, word, normalized).ratio(), label) for label in available for normalized in [normalize_text(label)]),
            key=lambda item: (-item[0], item[1]),
        )
        if matches and matches[0][0] >= 0.84 and (len(matches) == 1 or matches[0][0] - matches[1][0] >= 0.035):
            candidates.append((word, [label for score, label in matches if score >= 0.78][:4]))
    if not candidates:
        return None
    requested, options = candidates[0]
    return {
        "code": "profession_spelling",
        "message": "No pude confirmar ese oficio. Elegí una coincidencia del catálogo; la consulta no se enviará hasta que la vuelvas a buscar.",
        "requestedText": requested,
        "options": [{"kind": "profession", "name": name} for name in options],
    }


def _build_fts_expression(intent):
    values = [intent.search_text, intent.action_text, intent.object_text, intent.profession_text, *intent.related_terms]
    if intent.object_text:
        values.extend(aliases.object_aliases(intent.object_text))
    if intent.action_text:
        values.extend(aliases.action_aliases(intent.action_text))
    if intent.profession_text:
        values.extend(aliases.profession_aliases(intent.profession_text))
    query_terms = [word for word in unique_terms(values) if word not in aliases.SPANISH_STOP_WORDS]
    if not query_terms:
        return None
    # Every lexeme is double-quoted; FTS syntax comes only from this code, never the request.
    return " OR ".join('"' + term.replace('"', '""') + '"' for term in query_terms)


def _lexical_rankings(eligible_ids, intent):
    expression = _build_fts_expression(intent)
    if not eligible_ids or not expression:
        return []
    statement = text(
        "SELECT f.profile_id, f.source_hash, bm25(profile_search_fts, 2.2, 1.2, 1.5, 2.0, 1.3) AS score "
        "FROM profile_search_fts AS f "
        "JOIN profile_search_documents AS d ON d.profile_id=f.profile_id AND d.source_hash=f.source_hash "
        "JOIN profiles AS p ON p.id=f.profile_id "
        "WHERE profile_search_fts MATCH :match AND p.status='active' AND f.profile_id IN :ids "
        "ORDER BY score ASC LIMIT :limit"
    ).bindparams(bindparam("ids", expanding=True))
    rows = db.session.execute(statement, {"match": expression, "ids": sorted(eligible_ids), "limit": LEXICAL_POOL_SIZE}).all()
    return [(row.profile_id, row.source_hash) for row in rows]


def _semantic_rankings(eligible_ids, intent, config, encoder=None, query_vector=None):
    if not eligible_ids or not config.get("AI_SEARCH_SEMANTIC_ENABLED", True):
        return [], None, 0.0, 0.0, 0.0
    started = time.perf_counter()
    encoder = encoder or get_encoder(config)
    query_terms = [intent.search_text, *intent.related_terms]
    embedding_ms = 0.0
    if query_vector is None:
        embedding_started = time.perf_counter()
        query_vector = encode_normalized(encoder, [" ".join(value for value in query_terms if value)])[0]
        embedding_ms = (time.perf_counter() - embedding_started) * 1000
    else:
        query_vector = np.asarray(query_vector, dtype=np.float32).reshape(-1)
        norm = float(np.linalg.norm(query_vector))
        if query_vector.size != MODEL_DIMENSION or not np.isfinite(query_vector).all() or abs(norm - 1.0) > 1e-3:
            raise ValueError("El vector de consulta debe ser finito, normalizado y compatible.")
    scan_started = time.perf_counter()
    statement = select(ProfileSearchChunk, ProfileSearchDocument.source_hash).join(
        ProfileSearchDocument, ProfileSearchDocument.profile_id == ProfileSearchChunk.profile_id
    ).where(
        ProfileSearchChunk.profile_id.in_(eligible_ids),
        ProfileSearchChunk.source_hash == ProfileSearchDocument.source_hash,
        ProfileSearchChunk.encoder_model == MODEL_NAME,
        ProfileSearchChunk.encoder_revision == MODEL_REVISION,
        ProfileSearchChunk.vector_dimension == MODEL_DIMENSION,
        ProfileSearchChunk.vector_dtype == "float32-le",
    )
    best = {}
    for chunk, current_hash in db.session.execute(statement).all():
        if chunk.source_hash != current_hash or len(chunk.vector_bytes) != MODEL_DIMENSION * 4:
            continue
        vector = np.frombuffer(chunk.vector_bytes, dtype="<f4")
        if vector.shape != (MODEL_DIMENSION,) or not np.isfinite(vector).all():
            continue
        score = float(np.dot(vector, query_vector))
        if not np.isfinite(score):
            continue
        existing = best.get(chunk.profile_id)
        if existing is None or score > existing[0]:
            best[chunk.profile_id] = (score, chunk)
    ordered = sorted(best.items(), key=lambda item: (-item[1][0], item[0]))
    scan_ms = (time.perf_counter() - scan_started) * 1000
    return ordered[:SEMANTIC_SCORE_LIMIT], encoder, (time.perf_counter() - started) * 1000, embedding_ms, scan_ms


def _sentences(text_value):
    spans = []
    start = 0
    for match in re.finditer(r"[.!?]+\s+|\n+", text_value):
        end = match.end()
        if text_value[start:end].strip():
            spans.append(text_value[start:end].strip())
        start = end
    if text_value[start:].strip():
        spans.append(text_value[start:].strip())
    return spans or ([text_value.strip()] if text_value.strip() else [])


def _has_phrase(text_value, phrases):
    return any(contains_phrase(text_value, phrase) for phrase in phrases if phrase)


def _negates_requested_action(text_value, intent):
    if not intent.action_text:
        return False
    action, action_options = aliases.aliases_for(intent.action_text, aliases.ACTION_GROUPS)
    if action != "reparar":
        return False
    object_options = aliases.object_aliases(intent.object_text) if intent.object_text else ()
    if not object_options:
        return False
    sentences = _sentences(text_value)
    for index, sentence in enumerate(sentences):
        context = " ".join(sentences[max(0, index - 1):min(len(sentences), index + 2)])
        normalized = f" {normalize_text(context)} "
        has_object = _has_phrase(context, object_options)
        if not has_object:
            continue
        # “No solo reparo” is affirmative; all other matched negations are conservative exclusions.
        if re.search(r"\bno solo\b", normalized):
            normalized = re.sub(r"\bno solo\b", " ", normalized)
        negative_verb = re.search(r"\b(?:no|nunca|jamas)\s+(?:realizo\s+|hago\s+|ofrezco\s+|brindo\s+)?(?:" + "|".join(re.escape(normalize_text(v)) for v in action_options if normalize_text(v)) + r")\b", normalized)
        negative_service = re.search(
            r"\bno\s+(?:declaro|ofrezco|realizo|hago|brindo|presto|acepto)\b.{0,60}\b(?:"
            + "|".join(re.escape(normalize_text(v)) for v in action_options if normalize_text(v))
            + r")\b",
            normalized,
        )
        no_longer = re.search(r"\b(?:ya no|deje de|deje|no realizo|no hago)\b.*\b(?:servicio|trabajo|eso|ese|lo hago|lo realizo)\b", normalized)
        if negative_verb or negative_service or no_longer:
            return True
    return False


def _evidence_for_profile(profile, document, intent, semantic_entry, threshold):
    fields = {field: getattr(document, field) for field in ("profession", "category", "short_description", "description", "tags")}
    if intent.excluded_terms and any(contains_phrase(" ".join(fields.values()), term) for term in intent.excluded_terms):
        return None
    if _negates_requested_action(" ".join(fields.values()), intent):
        return None

    object_options = aliases.object_aliases(intent.object_text) if intent.object_text else ()
    action_options = aliases.action_aliases(intent.action_text) if intent.action_text else ()
    service_actions = tuple(value for group in aliases.ACTION_GROUPS.values() for value in group)
    direct_fields = []
    related_fields = []
    for field, value in fields.items():
        for sentence in _sentences(value):
            has_object = bool(object_options) and _has_phrase(sentence, object_options)
            has_action = bool(action_options) and _has_phrase(sentence, action_options)
            if intent.profession_text and field == "profession" and _has_phrase(value, aliases.profession_aliases(intent.profession_text)):
                direct_fields.append((field, sentence))
            if has_object and has_action:
                direct_fields.append((field, sentence))
            elif has_object and _has_phrase(sentence, service_actions):
                related_fields.append((field, sentence))

    if direct_fields:
        field, literal = direct_fields[0]
        return {"sourceField": field, "text": literal[:480], "matchType": "direct", "cosine": semantic_entry[0] if semantic_entry else None}
    if related_fields:
        field, literal = related_fields[0]
        return {"sourceField": field, "text": literal[:480], "matchType": "related", "cosine": semantic_entry[0] if semantic_entry else None}

    score, chunk = semantic_entry if semantic_entry else (None, None)
    if chunk and score >= threshold:
        anchored = _has_phrase(chunk.literal_text, (*object_options, *intent.related_terms))
        if anchored or score >= min(0.72, threshold + 0.12):
            return {
                "sourceField": chunk.source_field,
                "text": chunk.literal_text[:480],
                "matchType": "related",
                "cosine": score,
            }
    return None


def _location_label(profile, geo):
    locality = geo["locality"]
    department = geo["department"]
    if locality and profile.locality_id == locality.id:
        return f"En {profile.locality.name}"
    if locality:
        coverage = db.session.scalar(select(ProfileCoverage).where(
            ProfileCoverage.profile_id == profile.id,
            ProfileCoverage.locality_id == locality.id,
        ))
        if coverage:
            return f"Atiende en {locality.name}"
        return f"Atiende en {locality.name} (declaró cobertura departamental {locality.department.name})"
    if department and profile.department_id == department.id:
        return f"En {profile.locality.name}, {department.name}"
    if department:
        return f"Atiende en {department.name}"
    return f"En {profile.locality.name}, {profile.department.name}"


def search_profiles(
    intent, *, query, department_id=None, locality_id=None, limit=10, config,
    encoder=None, query_vector=None, serialize_profile, include_metrics=False, resolved_geography=None,
):
    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    parse_started = time.perf_counter()
    geo, clarification = resolved_geography or resolve_filters(query, intent.location_text, department_id, locality_id)
    if clarification:
        result = {
            "request_id": request_id, "status": "ambiguous", "message": clarification["message"],
            "applied_filters": {"department": None, "locality": None}, "clarification": clarification, "results": [],
        }
        if include_metrics:
            result["metrics"] = {"filter_ms": (time.perf_counter() - parse_started) * 1000, "fts_ms": 0.0, "query_embedding_ms": 0.0, "vector_scan_ms": 0.0, "retrieval_ms": 0.0, "total_ms": (time.perf_counter() - started) * 1000}
        return result
    applied_filters = {
        "department": geo["department"].name if geo["department"] else None,
        "departmentId": geo["department"].id if geo["department"] else None,
        "locality": geo["locality"].name if geo["locality"] else None,
        "localityId": geo["locality"].id if geo["locality"] else None,
        "locationSource": geo["source"],
        "profession": intent.profession_text,
    }
    _, profession_clarification = _profession_resolution(intent.profession_text)
    if profession_clarification:
        result = {
            "request_id": request_id, "status": "ambiguous", "message": profession_clarification["message"],
            "applied_filters": applied_filters,
            "clarification": profession_clarification, "results": [],
        }
        if include_metrics:
            result["metrics"] = {"filter_ms": (time.perf_counter() - parse_started) * 1000, "fts_ms": 0.0, "query_embedding_ms": 0.0, "vector_scan_ms": 0.0, "retrieval_ms": 0.0, "total_ms": (time.perf_counter() - started) * 1000}
        return result
    filter_ms = (time.perf_counter() - parse_started) * 1000
    eligible_ids = eligible_profile_ids(geo, intent.profession_text)
    if not eligible_ids:
        result = {
            "request_id": request_id, "status": "empty", "message": "No encontramos perfiles activos con esos filtros.",
            "applied_filters": applied_filters,
            "results": [],
        }
        if include_metrics:
            result["metrics"] = {"filter_ms": filter_ms, "fts_ms": 0.0, "query_embedding_ms": 0.0, "vector_scan_ms": 0.0, "retrieval_ms": 0.0, "total_ms": (time.perf_counter() - started) * 1000}
        return result

    retrieval_started = time.perf_counter()
    fts_started = time.perf_counter()
    lexical = _lexical_rankings(eligible_ids, intent)
    fts_ms = (time.perf_counter() - fts_started) * 1000
    semantic = []
    encoder_error = None
    semantic_ms = 0.0
    query_embedding_ms = 0.0
    vector_scan_ms = 0.0
    try:
        semantic, encoder, semantic_ms, query_embedding_ms, vector_scan_ms = _semantic_rankings(
            eligible_ids, intent, config, encoder, query_vector=query_vector
        )
    except Exception as exc:
        encoder_error = f"El índice semántico no está disponible ({type(exc).__name__})."
        logger.warning("advanced_search_encoder_failed request_id=%s error=%s", request_id, type(exc).__name__)

    lexical_rank = {profile_id: rank for rank, (profile_id, _source_hash) in enumerate(lexical, 1)}
    semantic_rank = {profile_id: rank for rank, (profile_id, _value) in enumerate(semantic, 1)}
    semantic_by_id = {profile_id: value for profile_id, value in semantic}
    cosine_threshold = float(config.get("AI_SEARCH_SEMANTIC_MIN_COSINE", 0.54))
    candidates = set(lexical_rank) | {profile_id for profile_id, (score, _chunk) in semantic if score >= cosine_threshold}
    combined = {
        profile_id: (1 / (RRF_CONSTANT + lexical_rank[profile_id]) if profile_id in lexical_rank else 0)
        + (1 / (RRF_CONSTANT + semantic_rank[profile_id]) if profile_id in semantic_rank else 0)
        for profile_id in candidates
    }
    ordered = sorted(candidates, key=lambda profile_id: (-combined[profile_id], profile_id))
    search_elapsed = (time.perf_counter() - retrieval_started) * 1000

    profile_rows = db.session.scalars(select(Profile).where(Profile.id.in_(ordered), Profile.status == "active")).all()
    profiles = {profile.id: profile for profile in profile_rows}
    documents = {row.profile_id: row for row in db.session.scalars(select(ProfileSearchDocument).where(ProfileSearchDocument.profile_id.in_(ordered))).all()}
    lexical_hashes = dict(lexical)
    results = []
    for profile_id in ordered:
        profile = profiles.get(profile_id)
        document = documents.get(profile_id)
        if not profile or not document:
            continue
        source_fields = profile_search_fields(profile)
        current_hash = hash_search_fields(source_fields)
        # Ignore any index output that raced with or predates a canonical profile edit.
        if document.source_hash != current_hash:
            continue
        if profile_id in lexical_hashes and lexical_hashes[profile_id] != current_hash:
            continue
        semantic_entry = semantic_by_id.get(profile_id)
        if semantic_entry and semantic_entry[1].source_hash != current_hash:
            semantic_entry = None
        evidence = _evidence_for_profile(profile, document, intent, semantic_entry, cosine_threshold)
        if not evidence:
            continue
        profile_payload = serialize_profile(profile)
        results.append({
            "profile": profile_payload,
            "evidence": evidence,
            "locationLabel": _location_label(profile, geo),
        })
        if len(results) >= limit:
            break

    elapsed = (time.perf_counter() - started) * 1000
    logger.info(
        "advanced_search request_id=%s eligible=%d lexical=%d semantic=%d results=%d filter_ms=%.1f "
        "semantic_ms=%.1f retrieval_ms=%.1f total_ms=%.1f degraded=%s",
        request_id, len(eligible_ids), len(lexical), len(semantic), len(results), filter_ms,
        semantic_ms, search_elapsed, elapsed, bool(encoder_error),
    )
    degraded = bool(encoder_error)
    message = "Sobre tu búsqueda, esto fue lo que pude encontrar." if results else "No encontré coincidencias suficientes entre los perfiles activos."
    if degraded:
        message += " La búsqueda semántica está temporalmente reducida; se usó texto y evidencia literal."
    result = {
        "request_id": request_id,
        "status": "degraded" if degraded else ("ok" if results else "empty"),
        "message": message,
        "applied_filters": applied_filters,
        "degradation": [encoder_error] if encoder_error else [],
        "results": results,
    }
    if include_metrics:
        result["metrics"] = {
            "filter_ms": filter_ms,
            "fts_ms": fts_ms,
            "query_embedding_ms": query_embedding_ms,
            "vector_scan_ms": vector_scan_ms,
            "retrieval_ms": search_elapsed,
            "total_ms": (time.perf_counter() - started) * 1000,
        }
    return result

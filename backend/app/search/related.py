"""Candidate generation and publication for the related-search pass."""

import re
from dataclasses import dataclass
from itertools import zip_longest

from sqlalchemy import select

from app.extensions import db
from app.models import Profile, ProfileSearchDocument

from .aliases import SPANISH_STOP_WORDS, object_aliases
from .catalog import eligible_profile_ids, eligible_profiles
from .documents import hash_search_fields, profile_search_fields
from .engine import (
    SERVICE_ACTIONS, _lexical_rankings, _location_label, _negates_requested_action,
    _semantic_rankings, _sentences,
)
from .reranker import rerank_scores
from .text import contains_number_variant, contains_phrase, normalize_text, number_forms, tokens


_GENERIC_WORDS = SPANISH_STOP_WORDS | {
    "mi", "mis", "sus", "este", "esta", "servicio", "servicios", "trabajo", "trabajos",
    "profesional", "profesionales", "ayuda", "revision", "diagnostico", "mantenimiento",
    *(normalize_text(action) for action in SERVICE_ACTIONS),
}
_LIMIT_WORDS = re.compile(r"\b(?:no|nunca|solo|solamente|unicamente|exclusivamente|excepto|salvo)\b")


@dataclass(frozen=True)
class RelatedCandidate:
    profile_id: str
    source_hash: str
    source_field: str
    excerpt: str
    verification_text: str


def _current_profiles(ids, geo, profession):
    statement = (
        select(Profile, ProfileSearchDocument)
        .join(ProfileSearchDocument, ProfileSearchDocument.profile_id == Profile.id)
        .where(Profile.id.in_(ids), Profile.status == "active")
        .execution_options(populate_existing=True)
    )
    rows = db.session.execute(eligible_profiles(statement, geo, profession))
    return {
        profile.id: (profile, document) for profile, document in rows
        if document.source_hash == hash_search_fields(profile_search_fields(profile))
    }


def _excerpt(document, chunk, signatures, required_terms):
    parts = []
    if chunk is not None and chunk.source_field in {"description", "short_description"}:
        literal = chunk.literal_text.strip()
        if literal in getattr(document, chunk.source_field):
            parts.append((chunk.source_field, literal))
    parts.extend((field, getattr(document, field).strip()) for field in ("description", "short_description"))
    for field, literal in parts:
        for text in (*_sentences(literal), literal):
            excerpt = text[:240]
            if _supports_query(excerpt, signatures, required_terms):
                return field, excerpt
    return None, ""


def _verification_text(document, excerpt):
    limits = dict.fromkeys(
        sentence[:100]
        for field in (document.short_description, document.description)
        for sentence in _sentences(field)
        if sentence not in excerpt and _LIMIT_WORDS.search(normalize_text(sentence))
    )
    return "\n".join((excerpt, *list(limits)[:2]))


def _semantic_excerpt(document, chunk):
    if chunk is not None and chunk.source_field in {"description", "short_description"}:
        literal = chunk.literal_text.strip()
        if literal and literal in getattr(document, chunk.source_field):
            return chunk.source_field, literal[:240]
    for field in ("short_description", "description"):
        literal = getattr(document, field).strip()
        if literal:
            return field, literal[:240]
    return None, ""


def _signature(text):
    return [
        forms for forms in (number_forms(word) for word in tokens(text) if len(word) > 2)
        if forms.isdisjoint(_GENERIC_WORDS)
    ]


def _supports_query(excerpt, signatures, required_terms):
    # Retrieval expansions are hypotheses. Require literal terms from a task or its broader service.
    words = set().union(*(number_forms(word) for word in tokens(excerpt)))
    return all(contains_number_variant(excerpt, term) for term in required_terms) and any(
        signature and all(forms & words for forms in signature) for signature in signatures
    )


def related_candidates(intent, *, query, geo, config, allow_semantic=False):
    eligible = eligible_profile_ids(geo, intent.profession_text)
    if not eligible:
        return []

    original = intent.model_copy(update={"search_text": query, "related_terms": []})
    original_vectors, *_ = _semantic_rankings(eligible, original, config)
    chunks = {pid: chunk for pid, (_score, chunk) in original_vectors}
    original_ids = [pid for pid, _ in original_vectors[:15]]

    # Keep the open-vocabulary alternatives independent of the strict interpretation.
    normalized_primary = {normalize_text(intent.search_text), normalize_text(query), ""}
    alternatives = {
        normalize_text(service): service for service in intent.related_services
        if normalize_text(service) not in normalized_primary
    }
    primary_signatures = [_signature(value) for value in object_aliases(intent.object_text)]
    object_words = set().union(*(set().union(*signature) for signature in primary_signatures))
    broader_services = []
    for service in alternatives.values():
        signature = _signature(service)
        words = set().union(*signature)
        # A rewrite that keeps only part of the same object's name can change its type.
        if signature and all(forms & object_words for forms in signature) and not any(
            primary and all(forms & words for forms in primary) for primary in primary_signatures
        ):
            continue
        if signature:
            broader_services.append((service, signature))
    signatures = primary_signatures + [signature for _, signature in broader_services]
    if not any(signatures):
        signatures = [_signature(intent.search_text)]
    alternative_ids = []
    representatives = []
    semantic_ids = set(original_ids[:3])
    for service, _signature_terms in broader_services:
        hypothesis = intent.model_copy(update={
            "search_text": service, "related_terms": [], "action_text": None,
            "object_text": None, "profession_text": None,
        })
        lexical = [pid for pid, _hash in _lexical_rankings(eligible, hypothesis)[:5]]
        semantic, *_ = _semantic_rankings(eligible, hypothesis, config)
        vector_ids = [pid for pid, _ in semantic[:5]]
        semantic_ids.update(vector_ids[:3])
        for pid, (_score, chunk) in semantic[:5]:
            if chunk.source_field in {"description", "short_description"}:
                chunks[pid] = chunk
        ids = list(dict.fromkeys(pid for pair in zip_longest(lexical, vector_ids) for pid in pair if pid))[:5]
        alternative_ids.extend(ids)
        representatives.extend(ids[:2])

    lexical_ids = [pid for pid, _hash in _lexical_rankings(eligible, intent)[:5]]
    pool = list(dict.fromkeys(original_ids + alternative_ids + lexical_ids))[:25]
    records = _current_profiles(pool, geo, intent.profession_text)
    anchored = {}
    semantic_fallback = {}
    for pid in pool:
        if pid not in records:
            continue
        _, document = records[pid]
        public_text = " ".join((document.profession, document.short_description, document.description, document.tags))
        if any(contains_phrase(public_text, term) for term in intent.excluded_terms):
            continue
        if _negates_requested_action(public_text, intent):
            continue
        field, excerpt = _excerpt(document, chunks.get(pid), signatures, intent.required_terms)
        destination = anchored
        if not excerpt and allow_semantic and broader_services and pid in semantic_ids:
            field, excerpt = _semantic_excerpt(document, chunks.get(pid))
            destination = semantic_fallback
        if excerpt:
            destination[pid] = RelatedCandidate(
                pid, document.source_hash, field, excerpt, _verification_text(document, excerpt),
            )

    candidates = anchored or semantic_fallback
    passages = [f"{records[pid][0].profession}\n{candidate.excerpt}" for pid, candidate in candidates.items()]
    scores = rerank_scores(query, passages, config)
    ranked = sorted(candidates, key=dict(zip(candidates, scores, strict=True)).__getitem__, reverse=True)
    # Reserve places for retrieved alternatives even when the cross-encoder favors lexical overlap.
    shortlist = []
    seen = set()
    original_representatives = original_ids[:2] if allow_semantic else []
    for pid in ranked[:2] + original_representatives + representatives + ranked:
        candidate = candidates.get(pid)
        if candidate is None:
            continue
        normalized = normalize_text(candidate.excerpt)
        if normalized not in seen:
            shortlist.append(candidate)
            seen.add(normalized)
        if len(shortlist) == 5:
            break
    return shortlist


def publish_suggestions(candidates, accepted, *, intent, geo, serialize_profile, limit):
    # Profiles and coverage may change while the local model verifies the excerpts.
    selected = [candidates[index - 1] for index in sorted(accepted)]
    records = _current_profiles({candidate.profile_id for candidate in selected}, geo, intent.profession_text)
    suggestions = []
    for candidate in selected:
        if candidate.profile_id not in records:
            continue
        profile, document = records[candidate.profile_id]
        if (document.source_hash != candidate.source_hash
                or candidate.excerpt not in getattr(document, candidate.source_field)):
            continue
        suggestions.append({
            "profile": serialize_profile(profile),
            "evidence": {
                "sourceField": candidate.source_field, "text": candidate.excerpt,
                "matchType": "related", "cosine": None,
            },
            "locationLabel": _location_label(profile, geo),
            "reason": "El perfil declara un servicio relacionado. Consultá si puede atender tu caso.",
        })
        if len(suggestions) == min(limit, 3):
            break
    return suggestions

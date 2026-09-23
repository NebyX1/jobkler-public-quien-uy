import hashlib
import json
import uuid

from sqlalchemy import delete, select, text

from app.extensions import db
from app.models import Category, Profile, ProfileSearchChunk, ProfileSearchDocument, ProfileSearchIndexJob
from app.models.jobkler import utcnow

from .model_manifest import CHUNK_PROCESSOR_VERSION, MODEL_NAME, MODEL_REVISION


SEARCH_FIELDS = ("profession", "category", "short_description", "description", "tags")


def profile_search_fields(profile):
    category = db.session.get(Category, profile.category_id) if profile.category_id else None
    return {
        "profession": profile.profession or "",
        "category": category.name if category else "",
        "short_description": profile.short_description or "",
        "description": profile.description or "",
        "tags": " ".join(tag.strip() for tag in (profile.tags or []) if isinstance(tag, str) and tag.strip()),
    }


def hash_search_fields(fields):
    payload = json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sync_profile_search(profile, *, force=False):
    """Update FTS and enqueue an idempotent embedding job in the profile transaction."""
    db.session.flush()
    fields = profile_search_fields(profile)
    source_hash = hash_search_fields(fields)
    search_text = "\n\n".join(value for value in fields.values() if value)
    document = db.session.get(ProfileSearchDocument, profile.id)
    changed = not document or document.source_hash != source_hash
    now = utcnow()

    if not document:
        document = ProfileSearchDocument(profile_id=profile.id, source_hash=source_hash, search_text=search_text, **fields)
        db.session.add(document)
    elif changed:
        document.source_hash = source_hash
        document.search_text = search_text
        for field, value in fields.items():
            setattr(document, field, value)
        document.updated_at = now

    if changed or force:
        db.session.execute(delete(ProfileSearchChunk).where(ProfileSearchChunk.profile_id == profile.id))
        db.session.execute(
            ProfileSearchIndexJob.__table__.update()
            .where(ProfileSearchIndexJob.profile_id == profile.id)
            .where(ProfileSearchIndexJob.status.in_(("pending", "failed", "running", "succeeded")))
            .where(ProfileSearchIndexJob.source_hash != source_hash)
            .values(status="superseded", updated_at=now, completed_at=now)
        )
        db.session.execute(text("DELETE FROM profile_search_fts WHERE profile_id = :profile_id"), {"profile_id": profile.id})

    if profile.status == "active":
        db.session.execute(text(
            "INSERT INTO profile_search_fts "
            "(profile_id, source_hash, profession, category, short_description, description, tags) "
            "VALUES (:profile_id, :source_hash, :profession, :category, :short_description, :description, :tags)"
        ), {"profile_id": profile.id, "source_hash": source_hash, **fields})
        chunks_exist = db.session.scalar(select(ProfileSearchChunk.chunk_id).where(
            ProfileSearchChunk.profile_id == profile.id,
            ProfileSearchChunk.source_hash == source_hash,
            ProfileSearchChunk.encoder_model == MODEL_NAME,
            ProfileSearchChunk.encoder_revision == MODEL_REVISION,
        ).limit(1))
        job = db.session.scalar(select(ProfileSearchIndexJob).where(
            ProfileSearchIndexJob.profile_id == profile.id,
            ProfileSearchIndexJob.source_hash == source_hash,
            ProfileSearchIndexJob.encoder_model == MODEL_NAME,
            ProfileSearchIndexJob.encoder_revision == MODEL_REVISION,
        ))
        if not chunks_exist and (not job or job.status in {"failed", "superseded"} or force):
            if not job:
                db.session.add(ProfileSearchIndexJob(
                    id=str(uuid.uuid4()), profile_id=profile.id, source_hash=source_hash,
                    encoder_model=MODEL_NAME, encoder_revision=MODEL_REVISION,
                    status="pending", attempts=0, next_attempt_at=now,
                ))
            else:
                job.status = "pending"
                job.attempts = 0
                job.next_attempt_at = now
                job.started_at = None
                job.completed_at = None
                job.last_error = None
                job.updated_at = now
    else:
        db.session.execute(text("DELETE FROM profile_search_fts WHERE profile_id = :profile_id"), {"profile_id": profile.id})
        db.session.execute(delete(ProfileSearchChunk).where(ProfileSearchChunk.profile_id == profile.id))
        db.session.execute(
            ProfileSearchIndexJob.__table__.update()
            .where(ProfileSearchIndexJob.profile_id == profile.id)
            .where(ProfileSearchIndexJob.status.in_(("pending", "failed")))
            .values(status="superseded", updated_at=now, completed_at=now)
        )
    return source_hash


def remove_profile_from_search(profile_id):
    db.session.execute(text("DELETE FROM profile_search_fts WHERE profile_id = :profile_id"), {"profile_id": profile_id})


def rebuild_search_documents(*, force=False):
    profiles = db.session.scalars(select(Profile).order_by(Profile.id)).all()
    for profile in profiles:
        sync_profile_search(profile, force=force)
    db.session.commit()
    return len(profiles)

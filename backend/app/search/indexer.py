import time
import uuid
from datetime import timedelta

from sqlalchemy import select, text

from app.extensions import db
from app.models import Profile, ProfileSearchDocument, ProfileSearchIndexJob
from app.models.jobkler import utcnow

from .encoder import encode_normalized, get_encoder, token_chunks, vector_record
from .model_manifest import MODEL_DIMENSION, MODEL_NAME, MODEL_REVISION

MAX_ATTEMPTS = 3
RUNNING_LEASE_SECONDS = 300


def enqueue_profile(profile, *, force=False):
    from .documents import sync_profile_search

    return sync_profile_search(profile, force=force)


def claim_next_job():
    now = utcnow()
    stale = now - timedelta(seconds=RUNNING_LEASE_SECONDS)
    with db.engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        connection.execute(text(
            "UPDATE profile_search_index_jobs SET status='failed', completed_at=:now, updated_at=:now, "
            "last_error=COALESCE(last_error, 'El worker se detuvo antes de terminar.') "
            "WHERE status='running' AND started_at < :stale AND attempts >= :max_attempts"
        ), {"now": now, "stale": stale, "max_attempts": MAX_ATTEMPTS})
        row = connection.execute(text(
            "SELECT id FROM profile_search_index_jobs "
            "WHERE (status IN ('pending','failed') AND attempts < :max_attempts AND next_attempt_at <= :now) "
            "OR (status = 'running' AND attempts < :max_attempts AND started_at < :stale) "
            "ORDER BY created_at, id LIMIT 1"
        ), {"max_attempts": MAX_ATTEMPTS, "now": now, "stale": stale}).first()
        if not row:
            connection.commit()
            return None
        job_id = row[0]
        connection.execute(text(
            "UPDATE profile_search_index_jobs SET status='running', attempts=attempts+1, "
            "started_at=:now, completed_at=NULL, last_error=NULL, updated_at=:now WHERE id=:id"
        ), {"now": now, "id": job_id})
        connection.commit()
        return job_id


def process_job(job_id, encoder):
    job = db.session.get(ProfileSearchIndexJob, job_id)
    profile = db.session.get(Profile, job.profile_id) if job else None
    document = db.session.get(ProfileSearchDocument, job.profile_id) if job else None
    if not job or not profile or not document or profile.status != "active" or document.source_hash != job.source_hash:
        if job:
            job.status = "superseded"
            job.completed_at = utcnow()
            job.updated_at = utcnow()
            db.session.commit()
        return "superseded"
    if job.status != "running" or job.encoder_model != MODEL_NAME or job.encoder_revision != MODEL_REVISION:
        db.session.rollback()
        return "superseded"

    profile_id = profile.id
    source_hash = document.source_hash
    fields = {field: getattr(document, field) for field in ("profession", "category", "short_description", "description", "tags")}
    attempts = job.attempts
    db.session.commit()

    chunks = token_chunks(encoder, profile_id, source_hash, fields)
    vectors = encode_normalized(encoder, [chunk["literal_text"] for chunk in chunks])
    for chunk, vector in zip(chunks, vectors, strict=True):
        chunk["vector_bytes"] = vector_record(vector)
        chunk["created_at"] = utcnow()

    now = utcnow()
    with db.engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        current = connection.execute(text(
            "SELECT p.status, d.source_hash, j.status, j.source_hash, j.encoder_model, j.encoder_revision "
            "FROM profile_search_index_jobs j JOIN profiles p ON p.id=j.profile_id "
            "JOIN profile_search_documents d ON d.profile_id=p.id WHERE j.id=:id"
        ), {"id": job_id}).first()
        if not current or current[0] != "active" or current[1] != source_hash or current[2] != "running" or current[3] != source_hash or current[4] != MODEL_NAME or current[5] != MODEL_REVISION:
            connection.execute(text(
                "UPDATE profile_search_index_jobs SET status='superseded', completed_at=:now, updated_at=:now WHERE id=:id AND status='running'"
            ), {"now": now, "id": job_id})
            connection.commit()
            return "superseded"
        connection.execute(text("DELETE FROM profile_search_chunks WHERE profile_id=:id"), {"id": profile_id})
        if chunks:
            connection.execute(ProfileSearchChunkTable.insert(), chunks)
        connection.execute(text(
            "UPDATE profile_search_index_jobs SET status='succeeded', completed_at=:now, updated_at=:now, last_error=NULL WHERE id=:id"
        ), {"now": now, "id": job_id})
        connection.commit()
    return "succeeded"


def process_one(encoder=None, *, config=None):
    job_id = claim_next_job()
    if not job_id:
        return "idle"
    try:
        if encoder is None:
            encoder = get_encoder(config)
        return process_job(job_id, encoder)
    except Exception as exc:
        db.session.rollback()
        job = db.session.get(ProfileSearchIndexJob, job_id)
        now = utcnow()
        if job and job.status == "running":
            job.status = "failed"
            job.last_error = f"{type(exc).__name__}: {exc}"[:500]
            job.next_attempt_at = now + timedelta(seconds=min(60, 5 * max(1, job.attempts)))
            job.completed_at = now
            job.updated_at = now
            db.session.commit()
        return "failed"


ProfileSearchChunkTable = __import__("app.models", fromlist=["ProfileSearchChunk"]).ProfileSearchChunk.__table__


def run_worker(app, *, poll_seconds=1.0, once=False):
    with app.app_context():
        try:
            encoder = get_encoder(app.config)
        except Exception as exc:
            raise RuntimeError(f"No se pudo iniciar el encoder CPU: {exc}") from exc
        while True:
            state = process_one(encoder, config=app.config)
            if once:
                return state
            if state == "idle":
                db.session.remove()
                time.sleep(poll_seconds)
            else:
                db.session.remove()

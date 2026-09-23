import hashlib
import hmac
import secrets
from datetime import timedelta

from flask import current_app, request

from app.extensions import db
from app.models import Account, AuthSession, Profile
from app.models.jobkler import utcnow


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def current_session():
    raw = request.cookies.get(current_app.config["AUTH_COOKIE_NAME"])
    if not raw:
        return None
    session = db.session.get(AuthSession, digest(raw))
    if not session or session.revoked_at or session.expires_at <= utcnow():
        return None
    if not session.account or session.account.status != "active":
        return None
    return session


def current_account():
    session = current_session()
    return session.account if session else None


def create_session(account, provider):
    old = current_session()
    if old:
        old.revoked_at = utcnow()
    raw = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    session = AuthSession(
        token_hash=digest(raw),
        account_id=account.id,
        provider=provider,
        csrf_hash=digest(csrf),
        expires_at=utcnow() + timedelta(seconds=current_app.config["SESSION_TTL_SECONDS"]),
    )
    db.session.add(session)
    db.session.commit()
    return raw, csrf


def revoke_current_session():
    session = current_session()
    if session:
        session.revoked_at = utcnow()
        db.session.commit()


def require_csrf():
    raw = request.cookies.get(current_app.config["CSRF_COOKIE_NAME"], "")
    header = request.headers.get("X-CSRF-Token", "")
    if not raw or not header or not hmac.compare_digest(raw, header):
        return False
    session = current_session()
    if session and not hmac.compare_digest(session.csrf_hash, digest(header)):
        return False
    return True


def account_payload(account, provider=None):
    profile = db.session.scalar(db.select(Profile.id).where(Profile.owner_id == account.id))
    roles = ["moderator"] if account.is_moderator else ["user"]
    return {
        "id": account.id,
        "fusionauth_user_id": account.id,
        "full_name": account.display_name,
        "first_name": account.display_name.split(" ", 1)[0],
        "last_name": account.display_name.split(" ", 1)[1] if " " in account.display_name else None,
        "email": account.email_private,
        "email_verified": account.email_verified,
        "picture": account.picture_url,
        "roles": roles,
        "auth_provider": provider or "fusionauth",
        "has_profile": profile is not None,
        "is_demo": provider == "demo",
    }

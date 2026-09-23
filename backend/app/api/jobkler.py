import re
import unicodedata
import uuid
from datetime import timezone

from flask import Blueprint, current_app, jsonify, request
from flask_limiter.util import get_remote_address
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.extensions import db, limiter
from app.models import Account, Category, Department, Locality, Profile, Review
from app.models.jobkler import utcnow
from app.services.sessions import account_payload, current_account, current_session, require_csrf

jobkler_bp = Blueprint("jobkler_api", __name__)
PROFILE_FIELDS = {
    "displayName": "display_name",
    "profession": "profession",
    "shortDescription": "short_description",
    "description": "description",
    "photoUrl": "photo_url",
    "phone": "phone",
    "whatsapp": "whatsapp",
    "email": "contact_email",
    "website": "website",
    "instagram": "instagram",
    "address": "address",
    "serviceArea": "service_area",
    "tags": "tags",
    "availability": "availability",
    "yearsExperience": "years_experience",
}
SYSTEM_FIELDS = {
    "ownerUserId", "owner_id", "ownerId", "verified", "rating", "reviewsCount",
    "featured", "roles", "status", "id", "slug", "createdAt", "updatedAt",
    "professionNormalized", "isModerator", "authorUserId", "authorName",
}
REVIEW_SYSTEM_FIELDS = {
    "authorUserId", "author_id", "authorId", "authorName", "status", "id",
    "createdAt", "updatedAt", "profileSlug", "editable",
}
DEMO_ACCOUNTS = (
    {"key": "client", "name": "Cliente Demo", "description": "Cuenta sin perfil; puede crear reseñas y un perfil."},
    {"key": "provider-a", "name": "Prestadora A · Valentina Duarte Demo", "description": "Sanitaria con perfil en Minas."},
    {"key": "provider-b", "name": "Prestador B · Bruno Silva Demo", "description": "Electricista con perfil en Solís de Mataojo."},
    {"key": "moderator", "name": "Moderación Demo", "description": "Puede ocultar reseñas reportadas."},
)


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(re.sub(r"[^a-zA-Z0-9]+", " ", value).casefold().split())


def clean_slug(value):
    return normalize(value).replace(" ", "-")


def api_error(message, status):
    return jsonify({"error": message}), status


def body_json():
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def require_user(mutate=False):
    account = current_account()
    if not account:
        return None, api_error("Iniciá sesión para continuar.", 401)
    if mutate and not require_csrf():
        return None, api_error("Token CSRF inválido o vencido.", 403)
    return account, None


def iso(value):
    if not value:
        return None
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def rating_data(profile_id):
    rating, count = db.session.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(
            Review.profile_id == profile_id, Review.status == "published"
        )
    ).one()
    return (round(float(rating), 1) if rating is not None else 0.0, int(count or 0))


def serialize_profile(profile, viewer=None):
    rating, count = rating_data(profile.id)
    return {
        "id": profile.id,
        "slug": profile.slug,
        "name": profile.display_name,
        "displayName": profile.display_name,
        "category": profile.category.name,
        "categoryId": profile.category_id,
        "profession": profile.profession,
        "professionNormalized": profile.profession_normalized,
        "department": profile.department.name,
        "departmentId": profile.department_id,
        "locality": profile.locality.name,
        "localityId": profile.locality_id,
        "shortDescription": profile.short_description,
        "description": profile.description,
        "photoUrl": profile.photo_url,
        "avatarFallback": "",
        "phone": profile.phone,
        "whatsapp": profile.whatsapp,
        "email": profile.contact_email,
        "website": profile.website,
        "instagram": profile.instagram,
        "address": profile.address,
        "serviceArea": profile.service_area or [],
        "tags": profile.tags or [],
        "availability": profile.availability,
        "verified": profile.verified,
        "rating": rating,
        "reviewsCount": count,
        "yearsExperience": profile.years_experience,
        "featured": profile.featured,
        "status": profile.status,
        "createdAt": iso(profile.created_at),
        "updatedAt": iso(profile.updated_at),
        "isOwner": bool(viewer and viewer.id == profile.owner_id),
        "isFictionalDemo": profile.is_demo_fixture,
    }


def serialize_review(review):
    return {
        "id": review.id,
        "profileId": review.profile_id,
        "profileSlug": review.profile.slug,
        "authorName": review.author.display_name,
        "authorPicture": review.author.picture_url or "",
        "rating": review.rating,
        "comment": review.comment,
        "status": review.status,
        "editable": False,
        "acceptedNoEditPolicy": True,
        "createdAt": iso(review.created_at),
        "updatedAt": iso(review.created_at),
    }


def resolve_catalog(model, value, identifier=None):
    candidates = [normalize(v) for v in (identifier, value) if v]
    if not candidates:
        return None
    rows = db.session.scalars(select(model)).all()
    matches = [
        row for row in rows
        if any(normalize(row.id) == candidate or normalize(row.slug) == candidate or normalize(row.name) == candidate for candidate in candidates)
    ]
    if not matches:
        return None
    if len({row.id for row in matches}) > 1:
        return None
    return matches[0]


def resolve_profile_values(data, profile=None):
    result = {}
    for public, model_field in PROFILE_FIELDS.items():
        if public in data:
            result[model_field] = data[public]
    category = resolve_catalog(Category, data.get("category"), data.get("categoryId")) if ("category" in data or "categoryId" in data) else (profile.category if profile else None)
    department = resolve_catalog(Department, data.get("department"), data.get("departmentId")) if ("department" in data or "departmentId" in data) else (profile.department if profile else None)
    locality = resolve_catalog(Locality, data.get("locality"), data.get("localityId")) if ("locality" in data or "localityId" in data) else (profile.locality if profile else None)
    if not category:
        raise ValueError("Elegí una categoría válida.")
    if not department or not locality:
        raise ValueError("Elegí un departamento y una localidad válidos.")
    if locality.department_id != department.id:
        raise ValueError("La localidad no pertenece al departamento seleccionado.")
    result.update(category_id=category.id, department_id=department.id, locality_id=locality.id)
    if not result.get("display_name"):
        result["display_name"] = data.get("displayName") or (profile.display_name if profile else "")
    if "profession" in result:
        result["profession_normalized"] = normalize(result["profession"])
    elif profile:
        result["profession_normalized"] = profile.profession_normalized
    for key in ("service_area", "tags"):
        if key in result and not isinstance(result[key], list):
            result[key] = [x.strip() for x in str(result[key] or "").split(",") if x.strip()]
    years = result.get("years_experience", profile.years_experience if profile else 0)
    try:
        years = int(years or 0)
    except (TypeError, ValueError):
        raise ValueError("Los años de experiencia deben ser un número entero.")
    if years < 0 or years > 100:
        raise ValueError("Los años de experiencia deben estar entre 0 y 100.")
    result["years_experience"] = years
    required = {
        "display_name": result.get("display_name"),
        "profession": result.get("profession", profile.profession if profile else ""),
        "short_description": result.get("short_description", profile.short_description if profile else ""),
        "description": result.get("description", profile.description if profile else ""),
    }
    if any(not str(value or "").strip() for value in required.values()):
        raise ValueError("Completá nombre, oficio y las dos descripciones.")
    for field, limit in (("display_name", 120), ("profession", 120), ("short_description", 240), ("description", 6000)):
        value = result.get(field, getattr(profile, field, "") if profile else "")
        if len(str(value or "").strip()) > limit:
            raise ValueError(f"El campo {field} supera el largo permitido.")
    return result


def update_search_text(profile):
    category = profile.category or db.session.get(Category, profile.category_id)
    department = profile.department or db.session.get(Department, profile.department_id)
    locality = profile.locality or db.session.get(Locality, profile.locality_id)
    values = [
        profile.display_name, profile.profession, profile.short_description, profile.description,
        category.name if category else "", department.name if department else "", locality.name if locality else "",
        " ".join(profile.tags or []), " ".join(profile.service_area or []),
    ]
    profile.search_text = normalize(" ".join(values))


def reject_system_fields(data):
    forbidden = SYSTEM_FIELDS.intersection(data)
    if forbidden:
        raise ValueError("No se pueden modificar campos de sistema: " + ", ".join(sorted(forbidden)))


@jobkler_bp.get("/auth/config")
def auth_config():
    from app.api.auth_routes import configured as fusionauth_configured
    return {
        "mode": current_app.config["AUTH_MODE"],
        "demoEnabled": current_app.config["AUTH_MODE"] == "demo" and current_app.config["ALLOW_DEMO_AUTH"],
        "configured": fusionauth_configured(),
        "loginUrl": "/api/auth/login/google" if current_app.config["AUTH_MODE"] == "fusionauth" else None,
        "aiSearchEnabled": current_app.config["AI_SEARCH_ENABLED"],
        "demoBanner": current_app.config["AUTH_MODE"] == "demo",
    }


@jobkler_bp.get("/auth/demo-accounts")
def demo_accounts():
    if current_app.config["AUTH_MODE"] != "demo" or not current_app.config["ALLOW_DEMO_AUTH"]:
        return api_error("El acceso de demostración no está habilitado.", 404)
    return {"accounts": DEMO_ACCOUNTS}


@jobkler_bp.get("/auth/csrf")
def csrf_token():
    session = current_session()
    token = request.cookies.get(current_app.config["CSRF_COOKIE_NAME"], "")
    if not token or (session and session.csrf_hash != __import__("hashlib").sha256(token.encode()).hexdigest()):
        import secrets
        from app.services.sessions import digest
        token = secrets.token_urlsafe(32)
        if session:
            session.csrf_hash = digest(token)
            db.session.commit()
    response = jsonify({"csrfToken": token})
    response.set_cookie(
        current_app.config["CSRF_COOKIE_NAME"], token,
        httponly=False, secure=current_app.config["AUTH_COOKIE_SECURE"],
        samesite=current_app.config["AUTH_COOKIE_SAMESITE"], path="/",
        max_age=current_app.config["SESSION_TTL_SECONDS"],
    )
    return response


@jobkler_bp.get("/auth/me")
def auth_me():
    session = current_session()
    if not session:
        return api_error("Iniciá sesión para continuar.", 401)
    return jsonify(account_payload(session.account, session.provider))


@jobkler_bp.post("/auth/demo-login")
@limiter.limit("8 per minute")
def demo_login():
    if current_app.config["AUTH_MODE"] != "demo" or not current_app.config["ALLOW_DEMO_AUTH"]:
        return api_error("El acceso de demostración no está habilitado.", 404)
    if not require_csrf():
        return api_error("Token CSRF inválido o vencido.", 403)
    key = body_json().get("key")
    allowed = {entry["key"] for entry in DEMO_ACCOUNTS}
    if key not in allowed:
        return api_error("Elegí una cuenta de demostración disponible.", 400)
    from app.models import Identity
    identity = db.session.scalar(select(Identity).where(
        Identity.provider == "demo",
        Identity.issuer == "jobkler-local-demo",
        Identity.subject == key,
    ))
    if not identity or identity.account.status != "active":
        return api_error("No se encontró esa cuenta de demostración.", 503)
    from app.services.sessions import create_session
    token, csrf = create_session(identity.account, "demo")
    response = jsonify(account_payload(identity.account, "demo"))
    response.set_cookie(
        current_app.config["AUTH_COOKIE_NAME"], token,
        httponly=True, secure=current_app.config["AUTH_COOKIE_SECURE"],
        samesite=current_app.config["AUTH_COOKIE_SAMESITE"], path="/",
        max_age=current_app.config["SESSION_TTL_SECONDS"],
    )
    response.set_cookie(
        current_app.config["CSRF_COOKIE_NAME"], csrf,
        httponly=False, secure=current_app.config["AUTH_COOKIE_SECURE"],
        samesite=current_app.config["AUTH_COOKIE_SAMESITE"], path="/",
        max_age=current_app.config["SESSION_TTL_SECONDS"],
    )
    return response


@jobkler_bp.post("/auth/logout")
def auth_logout():
    if not require_csrf():
        return api_error("Token CSRF inválido o vencido.", 403)
    from app.services.sessions import revoke_current_session
    revoke_current_session()
    response = jsonify({"ok": True})
    response.delete_cookie(current_app.config["AUTH_COOKIE_NAME"], path="/")
    response.delete_cookie(current_app.config["CSRF_COOKIE_NAME"], path="/")
    return response


@jobkler_bp.get("/home")
def home():
    active_count = db.session.scalar(select(func.count(Profile.id)).where(Profile.status == "active")) or 0
    category_count = db.session.scalar(select(func.count(func.distinct(Profile.category_id))).where(Profile.status == "active")) or 0
    department_count = db.session.scalar(select(func.count(func.distinct(Profile.department_id))).where(Profile.status == "active")) or 0
    review_count = db.session.scalar(select(func.count(Review.id)).join(Profile).where(Profile.status == "active", Review.status == "published")) or 0
    featured = db.session.scalars(select(Profile).where(Profile.status == "active", Profile.featured.is_(True)).order_by(Profile.display_name).limit(6)).all()
    return {
        "metrics": {"profiles": active_count, "categories": category_count, "departments": department_count, "reviews": review_count},
        "featured": [serialize_profile(p, current_account()) for p in featured],
    }


@jobkler_bp.get("/catalog")
def catalog():
    cats = db.session.scalars(select(Category).order_by(Category.sort_order, Category.name)).all()
    deps = db.session.scalars(select(Department).order_by(Department.sort_order, Department.name)).all()
    locs = db.session.scalars(select(Locality).order_by(Locality.department_id, Locality.sort_order, Locality.name)).all()
    category_counts = dict(db.session.execute(
        select(Profile.category_id, func.count(Profile.id)).where(Profile.status == "active").group_by(Profile.category_id)
    ).all())
    locality_counts = dict(db.session.execute(
        select(Profile.locality_id, func.count(Profile.id)).where(Profile.status == "active").group_by(Profile.locality_id)
    ).all())
    return {
        "categories": [{"id": c.id, "name": c.name, "slug": c.slug, "description": c.description, "icon": c.icon, "featured": c.featured, "sortOrder": c.sort_order, "count": category_counts.get(c.id, 0)} for c in cats],
        "departments": [{"id": d.id, "name": d.name, "slug": d.slug, "featured": d.featured, "sortOrder": d.sort_order} for d in deps],
        "localities": [{"id": l.id, "name": l.name, "slug": l.slug, "department": l.department.name, "departmentId": l.department_id, "departmentSlug": l.department.slug, "featured": l.featured, "sortOrder": l.sort_order, "profileCount": locality_counts.get(l.id, 0)} for l in locs],
    }


@jobkler_bp.get("/suggestions")
def suggestions():
    term = normalize(request.args.get("q", ""))
    if len(term) < 2:
        return {"suggestions": []}
    professions = db.session.scalars(
        select(Profile.profession).where(Profile.status == "active").distinct().order_by(Profile.profession).limit(100)
    ).all()
    matches = [p for p in professions if term in normalize(p)]
    return {"suggestions": matches[:10]}


@jobkler_bp.get("/profiles")
def list_profiles():
    filters = request.args
    query = select(Profile).where(Profile.status == "active")
    department = resolve_catalog(Department, filters.get("department"), filters.get("departmentId")) if filters.get("department") or filters.get("departmentId") else None
    locality = resolve_catalog(Locality, filters.get("locality"), filters.get("localityId")) if filters.get("locality") or filters.get("localityId") else None
    category = resolve_catalog(Category, filters.get("category"), filters.get("categoryId")) if filters.get("category") or filters.get("categoryId") else None
    if (filters.get("department") or filters.get("departmentId")) and not department:
        query = query.where(Profile.id == "__no_match__")
    if (filters.get("locality") or filters.get("localityId")) and not locality:
        query = query.where(Profile.id == "__no_match__")
    if (filters.get("category") or filters.get("categoryId")) and not category:
        query = query.where(Profile.id == "__no_match__")
    if department:
        query = query.where(Profile.department_id == department.id)
    if locality:
        query = query.where(Profile.locality_id == locality.id)
    if department and locality and locality.department_id != department.id:
        query = query.where(Profile.id == "__no_match__")
    if category:
        query = query.where(Profile.category_id == category.id)
    if filters.get("profession"):
        profession = "%" + normalize(filters.get("profession")) + "%"
        query = query.where(Profile.profession_normalized.like(profession))
    if filters.get("featured") in {"true", "1"}:
        query = query.where(Profile.featured.is_(True))
    if filters.get("featured") in {"false", "0"}:
        query = query.where(Profile.featured.is_(False))
    term = normalize(filters.get("q", ""))
    if term:
        for word in term.split():
            query = query.where(Profile.search_text.like(f"%{word}%"))
    page = max(1, min(100000, request.args.get("page", 1, type=int)))
    limit = max(1, min(50, request.args.get("limit", 12, type=int)))
    total = db.session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    profiles = db.session.scalars(query.order_by(Profile.featured.desc(), Profile.display_name).offset((page - 1) * limit).limit(limit)).all()
    return {
        "items": [serialize_profile(p, current_account()) for p in profiles],
        "total": int(total), "page": page, "limit": limit,
        "pages": (int(total) + limit - 1) // limit,
    }


@jobkler_bp.get("/profiles/me")
def my_profile():
    account, error = require_user()
    if error:
        return error
    profile = db.session.scalar(select(Profile).where(Profile.owner_id == account.id))
    if not profile:
        return api_error("Todavía no tenés un perfil profesional.", 404)
    return jsonify(serialize_profile(profile, account))


@jobkler_bp.get("/profiles/<string:profile_key>")
def get_profile(profile_key):
    profile = db.session.scalar(select(Profile).where(or_(Profile.id == profile_key, Profile.slug == profile_key)))
    viewer = current_account()
    if not profile or (profile.status != "active" and (not viewer or viewer.id != profile.owner_id)):
        return api_error("Perfil no encontrado.", 404)
    return jsonify(serialize_profile(profile, viewer))


@jobkler_bp.post("/profiles")
@limiter.limit("20 per hour")
def create_profile():
    account, error = require_user(mutate=True)
    if error:
        return error
    data = body_json()
    try:
        reject_system_fields(data)
        values = resolve_profile_values(data)
    except ValueError as exc:
        return api_error(str(exc), 400)
    if db.session.scalar(select(Profile.id).where(Profile.owner_id == account.id)):
        return api_error("Cada cuenta puede tener un perfil. Ya existe uno para esta cuenta.", 409)
    profile_id = "profile-" + uuid.uuid4().hex
    slug = clean_slug(f"{values['display_name']} {values['profession']} {db.session.get(Locality, values['locality_id']).name}")
    if not slug:
        return api_error("No se pudo crear un enlace para el perfil.", 400)
    profile = Profile(id=profile_id, slug=slug, owner_id=account.id, **values, status="active")
    profile.verified = False
    profile.featured = False
    update_search_text(profile)
    db.session.add(profile)
    try:
        db.session.flush()
        from app.search.catalog import resolve_coverage_values
        from app.search.documents import sync_profile_search
        resolve_coverage_values(profile.id, profile.service_area)
        sync_profile_search(profile)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_error("Ya existe un perfil o enlace con esos datos.", 409)
    return jsonify(serialize_profile(profile, account)), 201


@jobkler_bp.patch("/profiles/<string:profile_key>")
def update_profile(profile_key):
    account, error = require_user(mutate=True)
    if error:
        return error
    profile = db.session.scalar(select(Profile).where(or_(Profile.id == profile_key, Profile.slug == profile_key)))
    if not profile:
        return api_error("Perfil no encontrado.", 404)
    if profile.owner_id != account.id:
        return api_error("No tenés permiso para modificar este perfil.", 403)
    data = body_json()
    try:
        reject_system_fields(data)
        values = resolve_profile_values(data, profile)
    except ValueError as exc:
        return api_error(str(exc), 400)
    for key, value in values.items():
        setattr(profile, key, value)
    profile.updated_at = utcnow()
    update_search_text(profile)
    try:
        from app.search.catalog import resolve_coverage_values
        from app.search.documents import sync_profile_search
        resolve_coverage_values(profile.id, profile.service_area)
        sync_profile_search(profile)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_error("No se pudo guardar por un conflicto de datos.", 409)
    return jsonify(serialize_profile(profile, account))


@jobkler_bp.post("/profiles/<string:profile_key>/status")
def set_profile_status(profile_key):
    account, error = require_user(mutate=True)
    if error:
        return error
    profile = db.session.scalar(select(Profile).where(or_(Profile.id == profile_key, Profile.slug == profile_key)))
    if not profile:
        return api_error("Perfil no encontrado.", 404)
    if profile.owner_id != account.id:
        return api_error("No tenés permiso para modificar este perfil.", 403)
    status = body_json().get("status")
    if status not in {"active", "inactive"}:
        return api_error("El estado debe ser active o inactive.", 400)
    profile.status = status
    profile.updated_at = utcnow()
    from app.search.documents import sync_profile_search
    sync_profile_search(profile)
    db.session.commit()
    return jsonify(serialize_profile(profile, account))


@jobkler_bp.delete("/profiles/<string:profile_key>")
def delete_profile(profile_key):
    account, error = require_user(mutate=True)
    if error:
        return error
    profile = db.session.scalar(select(Profile).where(or_(Profile.id == profile_key, Profile.slug == profile_key)))
    if not profile:
        return api_error("Perfil no encontrado.", 404)
    if profile.owner_id != account.id:
        return api_error("No tenés permiso para eliminar este perfil.", 403)
    from app.search.documents import remove_profile_from_search
    remove_profile_from_search(profile.id)
    db.session.delete(profile)
    db.session.commit()
    return "", 204


@jobkler_bp.get("/reviews")
def list_reviews():
    profile_id = request.args.get("profileId")
    author_id = request.args.get("authorUserId")
    query = select(Review)
    if author_id:
        account, error = require_user()
        if error:
            return error
        if author_id != account.id:
            return api_error("No tenés permiso para consultar las reseñas de otra cuenta.", 403)
        query = query.where(Review.author_id == account.id)
    else:
        query = query.where(Review.status == "published")
        if profile_id:
            profile = db.session.scalar(select(Profile).where(Profile.id == profile_id))
            if not profile or profile.status != "active":
                return jsonify([])
            query = query.where(Review.profile_id == profile_id)
    reviews = db.session.scalars(query.order_by(Review.created_at.desc())).all()
    return jsonify([serialize_review(r) for r in reviews])


@jobkler_bp.post("/reviews")
@limiter.limit("12 per hour")
def create_review():
    account, error = require_user(mutate=True)
    if error:
        return error
    data = body_json()
    if REVIEW_SYSTEM_FIELDS.intersection(data):
        return api_error("La identidad del autor y el estado los determina el servidor.", 400)
    profile = db.session.get(Profile, str(data.get("profileId", "")))
    if not profile or profile.status != "active":
        return api_error("Perfil no encontrado.", 404)
    if profile.owner_id == account.id:
        return api_error("No podés reseñar tu propio perfil.", 403)
    try:
        rating = int(data.get("rating"))
    except (TypeError, ValueError):
        return api_error("La puntuación debe ser un número entero entre 1 y 5.", 400)
    comment = str(data.get("comment", "")).strip()
    if rating not in range(1, 6):
        return api_error("La puntuación debe estar entre 1 y 5.", 400)
    if len(comment) < 10 or len(comment) > 500:
        return api_error("El comentario debe tener entre 10 y 500 caracteres.", 400)
    if data.get("acceptedNoEditPolicy") is not True:
        return api_error("Confirmá que la reseña no se puede editar después de publicarla.", 400)
    review = Review(id="review-" + uuid.uuid4().hex, profile_id=profile.id, author_id=account.id, rating=rating, comment=comment)
    db.session.add(review)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_error("Ya publicaste una reseña para este perfil.", 409)
    return jsonify(serialize_review(review)), 201


@jobkler_bp.patch("/moderation/reviews/<string:review_id>")
def moderate_review(review_id):
    account, error = require_user(mutate=True)
    if error:
        return error
    if not account.is_moderator:
        return api_error("Necesitás permiso de moderación.", 403)
    review = db.session.get(Review, review_id)
    if not review:
        return api_error("Reseña no encontrada.", 404)
    status = body_json().get("status")
    if status not in {"published", "hidden"}:
        return api_error("El estado de reseña no es válido.", 400)
    review.status = status
    db.session.commit()
    return jsonify(serialize_review(review))

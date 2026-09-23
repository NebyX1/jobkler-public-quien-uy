from urllib.parse import urlsplit
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, redirect, request
from itsdangerous import URLSafeTimedSerializer

from app.extensions import db, limiter
from app.models import Account, Identity
from app.services.sessions import account_payload, create_session
from .fusionauth import (
    FusionAuthError,
    build_authorization_url,
    exchange_code_for_tokens,
    generate_pkce_pair,
    generate_state,
    get_userinfo,
    normalize_user,
    validate_id_token,
)

fusionauth_bp = Blueprint("fusionauth_auth", __name__, url_prefix="/api/auth")


def configured():
    cfg = current_app.config
    return bool(cfg["AUTH_MODE"] == "fusionauth" and all(
        cfg.get(k) for k in (
            "FUSIONAUTH_BASE_URL", "FUSIONAUTH_ISSUER", "FUSIONAUTH_CLIENT_ID",
            "FUSIONAUTH_CLIENT_SECRET", "FUSIONAUTH_GOOGLE_IDP_ID",
        )
    ))


def safe_frontend_redirect(path="/"):
    cfg = current_app.config
    base = urlsplit(cfg["FRONTEND_URL"])
    candidate = urlsplit(cfg["FRONTEND_URL"] + path)
    if candidate.scheme != base.scheme or candidate.netloc != base.netloc or not candidate.path.startswith("/"):
        candidate = base
    allowed_origins = set()
    for raw in cfg["AUTH_ALLOWED_REDIRECT_URLS"]:
        parts = urlsplit(raw)
        allowed_origins.add((parts.scheme, parts.netloc))
    if allowed_origins and (candidate.scheme, candidate.netloc) not in allowed_origins:
        candidate = base
    return candidate.geturl()


def state_serializer():
    return URLSafeTimedSerializer(current_app.config["AUTH_SESSION_SECRET"], salt="jobkler-oidc-state")


def cookie_flags():
    cfg = current_app.config
    return {
        "secure": cfg["AUTH_COOKIE_SECURE"],
        "samesite": cfg["AUTH_COOKIE_SAMESITE"],
        "path": "/",
    }


@fusionauth_bp.get("/login")
@limiter.limit("10 per minute")
def login():
    if current_app.config["AUTH_MODE"] != "fusionauth":
        return jsonify({"error": "El modo FusionAuth no está activo."}), 404
    if not configured():
        return jsonify({"error": "FusionAuth no está configurado. Configurá la instancia y las credenciales para iniciar sesión."}), 503
    cfg = current_app.config
    state = generate_state()
    verifier, challenge = generate_pkce_pair()
    state_cookie = state_serializer().dumps({"state": state, "verifier": verifier})
    authorize_url = build_authorization_url(
        base_url=cfg["FUSIONAUTH_BASE_URL"], client_id=cfg["FUSIONAUTH_CLIENT_ID"],
        redirect_uri=cfg["FUSIONAUTH_REDIRECT_URI"], state=state,
        code_challenge=challenge,
    )
    response = redirect(authorize_url)
    response.set_cookie("jobkler_oidc_state", state_cookie, httponly=True, max_age=600, **cookie_flags())
    return response


@fusionauth_bp.get("/login/google")
def login_google():
    if current_app.config["AUTH_MODE"] != "fusionauth":
        return jsonify({"error": "El modo FusionAuth no está activo."}), 404
    if not configured():
        return jsonify({"error": "FusionAuth y su proveedor Google no están configurados."}), 503
    cfg = current_app.config
    state = generate_state()
    verifier, challenge = generate_pkce_pair()
    state_cookie = state_serializer().dumps({"state": state, "verifier": verifier})
    authorize_url = build_authorization_url(
        base_url=cfg["FUSIONAUTH_BASE_URL"], client_id=cfg["FUSIONAUTH_CLIENT_ID"],
        redirect_uri=cfg["FUSIONAUTH_REDIRECT_URI"], state=state,
        code_challenge=challenge, idp_hint=cfg["FUSIONAUTH_GOOGLE_IDP_ID"],
        prompt="login", max_age=0,
    )
    response = redirect(authorize_url)
    response.set_cookie("jobkler_oidc_state", state_cookie, httponly=True, max_age=600, **cookie_flags())
    return response


@fusionauth_bp.get("/callback")
@limiter.limit("20 per minute")
def callback():
    if not configured():
        return jsonify({"error": "FusionAuth no está configurado."}), 503
    error = request.args.get("error")
    if error:
        response = redirect(safe_frontend_redirect("/login?error=login_failed"))
        response.delete_cookie("jobkler_oidc_state", **cookie_flags())
        return response
    code, state = request.args.get("code", ""), request.args.get("state", "")
    signed_state = request.cookies.get("jobkler_oidc_state", "")
    try:
        state_data = state_serializer().loads(signed_state, max_age=600)
    except Exception:
        state_data = None
    if not code or not state or not state_data or state_data.get("state") != state:
        return jsonify({"error": "El estado de autenticación es inválido o venció."}), 400

    cfg = current_app.config
    try:
        tokens = exchange_code_for_tokens(
            base_url=cfg["FUSIONAUTH_BASE_URL"], client_id=cfg["FUSIONAUTH_CLIENT_ID"],
            client_secret=cfg["FUSIONAUTH_CLIENT_SECRET"], redirect_uri=cfg["FUSIONAUTH_REDIRECT_URI"],
            code=code, code_verifier=state_data["verifier"], debug=False,
        )
        claims = validate_id_token(
            id_token=tokens.get("id_token", ""), issuer=cfg["FUSIONAUTH_ISSUER"],
            client_id=cfg["FUSIONAUTH_CLIENT_ID"],
            jwks_uri=cfg["FUSIONAUTH_BASE_URL"].rstrip("/") + "/.well-known/jwks.json",
        )
        if not claims.get("sub"):
            raise FusionAuthError("El ID token no contiene subject.")
        info = get_userinfo(base_url=cfg["FUSIONAUTH_BASE_URL"], access_token=tokens.get("access_token", "")) if tokens.get("access_token") else None
        if info and info.get("sub") != claims.get("sub"):
            raise FusionAuthError("El subject de UserInfo no coincide con el ID token.")
        user = normalize_user(id_token_claims=claims, userinfo_data=info)
    except FusionAuthError:
        return redirect(safe_frontend_redirect("/login?error=auth_failed"))

    issuer = cfg["FUSIONAUTH_ISSUER"].rstrip("/")
    identity = db.session.scalar(db.select(Identity).where(
        Identity.provider == "fusionauth", Identity.issuer == issuer, Identity.subject == user["fusionauth_user_id"]
    ))
    if identity:
        account = identity.account
        if account.status != "active":
            return jsonify({"error": "La cuenta está deshabilitada."}), 403
        account.display_name = user["full_name"] or account.display_name
        account.email_private = user["email"]
        account.email_verified = bool(user["email_verified"])
        account.picture_url = user["picture"]
    else:
        # No account is linked by email. Privileges are assigned only by local policy.
        account = Account(
            id="account-" + uuid4().hex, display_name=user["full_name"] or "Usuario",
            email_private=user["email"], email_verified=bool(user["email_verified"]),
            picture_url=user["picture"], is_moderator=False,
        )
        db.session.add(account)
        db.session.flush()
        db.session.add(Identity(
            id=str(uuid4()), account_id=account.id, provider="fusionauth",
            issuer=issuer, subject=user["fusionauth_user_id"],
        ))
    db.session.commit()
    raw_session, csrf = create_session(account, "fusionauth")
    response = redirect(safe_frontend_redirect("/"))
    response.set_cookie(cfg["AUTH_COOKIE_NAME"], raw_session, httponly=True, max_age=cfg["SESSION_TTL_SECONDS"], **cookie_flags())
    response.set_cookie(cfg["CSRF_COOKIE_NAME"], csrf, httponly=False, max_age=cfg["SESSION_TTL_SECONDS"], **cookie_flags())
    response.delete_cookie("jobkler_oidc_state", **cookie_flags())
    return response

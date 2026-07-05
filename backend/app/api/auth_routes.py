"""FusionAuth authentication routes.

Blueprint: ``fusionauth_bp`` (registered under ``/api/auth``)

Routes:
  GET  /api/auth/login     — starts the OAuth2 Authorization Code
                             flow with PKCE, redirects to FusionAuth.
  GET  /api/auth/callback  — receives the authorization code, exchanges
                             it for tokens, validates the ID token,
                             creates a session cookie, redirects to
                             the frontend.
  GET  /api/auth/me        — returns the current authenticated user
                             from the session cookie.
  POST /api/auth/logout    — clears the session cookie.
  GET  /api/auth/config     — returns non-secret public auth config
                             (used by the frontend to know if auth
                             is configured).
  GET  /api/auth/debug     — development-only diagnostics.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    request,
)
from itsdangerous import URLSafeTimedSerializer

from .fusionauth import (
    FusionAuthError,
    build_authorization_url,
    create_session_cookie,
    exchange_code_for_tokens,
    generate_pkce_pair,
    generate_state,
    get_userinfo,
    normalize_user,
    read_session_cookie,
    validate_id_token,
)

logger = logging.getLogger(__name__)

fusionauth_bp = Blueprint("fusionauth_auth", __name__, url_prefix="/api/auth")


# ── Helpers ─────────────────────────────────────────────────────────
def _get_config() -> Dict[str, Any]:
    """Read FusionAuth config from the Flask app config."""
    cfg = current_app.config
    return {
        "base_url": cfg.get("FUSIONAUTH_BASE_URL", ""),
        "issuer": cfg.get("FUSIONAUTH_ISSUER", ""),
        "client_id": cfg.get("FUSIONAUTH_CLIENT_ID", ""),
        "client_secret": cfg.get("FUSIONAUTH_CLIENT_SECRET", ""),
        "redirect_uri": cfg.get("FUSIONAUTH_REDIRECT_URI", ""),
        "frontend_url": cfg.get("FRONTEND_URL", ""),
        "session_secret": cfg.get("AUTH_SESSION_SECRET", ""),
        "cookie_name": cfg.get("AUTH_COOKIE_NAME", "quien_session"),
        "cookie_secure": cfg.get("AUTH_COOKIE_SECURE", False),
        "cookie_samesite": cfg.get("AUTH_COOKIE_SAMESITE", "Lax"),
        "allowed_redirects": cfg.get("AUTH_ALLOWED_REDIRECT_URLS", ()),
        "google_idp_id": cfg.get("FUSIONAUTH_GOOGLE_IDP_ID", ""),
        "force_max_age0": cfg.get("FUSIONAUTH_FORCE_MAX_AGE0", True),
    }


def _is_configured() -> bool:
    cfg = _get_config()
    return bool(cfg["client_id"] and cfg["client_secret"] and cfg["base_url"])


def _is_dev_mode() -> bool:
    """Return ``True`` when running outside of production, used to
    gate verbose (but always secret-free) FusionAuth diagnostics."""
    return current_app.config.get("ENV_NAME") != "production"


def _redact_authorize_url(url: str) -> str:
    """Return the authorize URL with the ``state`` and
    ``code_challenge`` values redacted, safe to log. Neither value is
    a secret (the PKCE verifier that would let someone abuse
    ``code_challenge`` never leaves the backend), but they uniquely
    identify a specific pending login attempt so we redact them out
    of caution.
    """
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    for key in ("state", "code_challenge"):
        if key in query:
            query[key] = "<redacted>"
    new_query = urlencode(query)
    redacted = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, new_query, parts.fragment)
    )
    # Append a human-readable summary of the forced-login params so
    # dev logs clearly show whether idp_hint / prompt / max_age are
    # present without exposing any sensitive value.
    flags = []
    if "idp_hint" in query:
        flags.append(f"idp_hint={query['idp_hint']}")
    if "prompt" in query:
        flags.append(f"prompt={query['prompt']}")
    if "max_age" in query:
        flags.append(f"max_age={query['max_age']}")
    if flags:
        redacted += "  [" + ", ".join(flags) + "]"
    return redacted


def _serialize_state(state_data: Dict[str, Any], secret: str) -> str:
    """Serialize state data (state + pkce_verifier) into a signed,
    tamper-proof token for the cookie.
    """
    serializer = URLSafeTimedSerializer(secret, salt="fusionauth-state")
    return serializer.dumps(state_data)


def _deserialize_state(
    token: str,
    secret: str,
    max_age: int = 600,
) -> Optional[Dict[str, Any]]:
    """Deserialize and verify the state token. Returns ``None`` on
    any error (expired, tampered, etc.). Max age defaults to 10 min.
    """
    try:
        serializer = URLSafeTimedSerializer(secret, salt="fusionauth-state")
        return serializer.loads(token, max_age=max_age)
    except Exception:
        return None


def _get_current_user() -> Optional[Dict[str, Any]]:
    """Read the current user from the session cookie."""
    cfg = _get_config()
    cookie_name = cfg["cookie_name"]
    cookie_value = request.cookies.get(cookie_name)
    if not cookie_value:
        return None
    return read_session_cookie(cookie_value, cfg["session_secret"])


def _set_session_cookie(resp, user: Dict[str, Any]) -> None:
    """Set the session cookie on a response."""
    cfg = _get_config()
    cookie_value = create_session_cookie(user, cfg["session_secret"])
    resp.set_cookie(
        cfg["cookie_name"],
        cookie_value,
        httponly=True,
        secure=cfg["cookie_secure"],
        samesite=cfg["cookie_samesite"],
        max_age=86400,  # 24 hours
        path="/",
    )


def _clear_session_cookie(resp) -> None:
    """Clear the session cookie on a response."""
    cfg = _get_config()
    resp.delete_cookie(
        cfg["cookie_name"],
        path="/",
        secure=cfg["cookie_secure"],
        samesite=cfg["cookie_samesite"],
        httponly=True,
    )


def _validate_redirect_url(url: str, allowed: tuple) -> str:
    """Validate that ``url`` starts with one of the allowed redirect
    URLs. Falls back to the first allowed URL if invalid (prevents
    open redirects).
    """
    for allowed_url in allowed:
        if url.startswith(allowed_url):
            return url
    return allowed[0] if allowed else "/"


def start_fusionauth_login(
    *,
    provider: Optional[str] = None,
    force: bool = False,
):
    """Start the OAuth2 Authorization Code flow with PKCE."""
    if not _is_configured():
        return jsonify({
            "error": "FusionAuth is not configured. "
            "Set FUSIONAUTH_CLIENT_ID and FUSIONAUTH_CLIENT_SECRET."
        }), 503

    cfg = _get_config()
    idp_hint = ""
    prompt = ""
    max_age = None

    if provider == "google":
        if not cfg["google_idp_id"]:
            return jsonify({
                "error": "FusionAuth Google IdP is not configured. "
                "Set FUSIONAUTH_GOOGLE_IDP_ID."
            }), 503
        idp_hint = cfg["google_idp_id"]
        prompt = "login"
        max_age = 0 if cfg["force_max_age0"] else None

    state = generate_state()
    code_verifier, code_challenge = generate_pkce_pair()

    state_data = {
        "state": state,
        "code_verifier": code_verifier,
    }
    state_cookie = _serialize_state(state_data, cfg["session_secret"])

    auth_url = build_authorization_url(
        base_url=cfg["base_url"],
        client_id=cfg["client_id"],
        redirect_uri=cfg["redirect_uri"],
        state=state,
        code_challenge=code_challenge,
        idp_hint=idp_hint,
        prompt=prompt,
        max_age=max_age,
    )

    if _is_dev_mode():
        logger.info(
            "[fusionauth] authorize URL (state/code_challenge redacted): %s",
            _redact_authorize_url(auth_url),
        )
        logger.info(
            "[fusionauth] login provider=%s force=%s redirect_uri=%s "
            "client_id=%s idp_hint=%s prompt=%s max_age=%s",
            provider or "generic",
            force,
            cfg["redirect_uri"],
            cfg["client_id"],
            idp_hint or "off",
            prompt or "off",
            max_age if max_age is not None else "off",
        )

    resp = redirect(auth_url)
    if force:
        _clear_session_cookie(resp)
    resp.set_cookie(
        "quien_auth_state",
        state_cookie,
        httponly=True,
        secure=cfg["cookie_secure"],
        samesite=cfg["cookie_samesite"],
        max_age=600,  # 10 minutes
        path="/",
    )
    return resp


# ── Routes ─────────────────────────────────────────────────────────
@fusionauth_bp.route("/login", methods=["GET"])
def login():
    """Start the OAuth2 Authorization Code flow with PKCE.

    Generates state + PKCE verifier, stores them in a short-lived
    signed cookie, and redirects to FusionAuth ``/oauth2/authorize``.
    """
    return start_fusionauth_login()


@fusionauth_bp.route("/login/google", methods=["GET"])
def login_google():
    """Force a fresh Google login through FusionAuth.

    Always starts a brand-new OAuth2 Authorization Code + PKCE flow
    targeting the Google Identity Provider via ``idp_hint``. Before
    generating the authorize URL, clears any existing local backend
    session cookie so stale sessions are never reused.

    The ``?force=1`` query param is accepted for frontend
    compatibility but is not required — this route always forces a
    fresh flow.
    """
    return start_fusionauth_login(provider="google", force=True)


@fusionauth_bp.route("/callback", methods=["GET"])
def callback():
    """Handle the OAuth2 callback from FusionAuth.

    Validates state, exchanges the code for tokens, validates the
    ID token, normalizes the user, creates a session cookie, and
    redirects to the frontend.
    """
    if not _is_configured():
        return jsonify({"error": "FusionAuth is not configured."}), 503

    cfg = _get_config()
    code = request.args.get("code", "")
    state = request.args.get("state", "")
    error = request.args.get("error", "")
    error_desc = request.args.get("error_description", "")

    if error:
        logger.warning(
            "[fusionauth] OAuth callback error: %s — %s", error, error_desc
        )
        frontend = _validate_redirect_url(
            f"{cfg['frontend_url']}/auth?error=login_failed",
            cfg["allowed_redirects"],
        )
        return redirect(frontend)

    if not code or not state:
        return jsonify({"error": "Missing code or state parameter."}), 400

    # Validate state against the short-lived cookie.
    state_cookie = request.cookies.get("quien_auth_state", "")
    if not state_cookie:
        return jsonify({"error": "Missing state cookie."}), 400

    state_data = _deserialize_state(state_cookie, cfg["session_secret"])
    if not state_data or state_data.get("state") != state:
        return jsonify({"error": "Invalid or expired state."}), 400

    code_verifier = state_data.get("code_verifier", "")

    # Exchange the code for tokens.
    try:
        token_data = exchange_code_for_tokens(
            base_url=cfg["base_url"],
            client_id=cfg["client_id"],
            client_secret=cfg["client_secret"],
            redirect_uri=cfg["redirect_uri"],
            code=code,
            code_verifier=code_verifier,
            debug=_is_dev_mode(),
        )
    except FusionAuthError as exc:
        error_code = getattr(exc, "error_code", "token_exchange_failed")
        logger.warning(
            "[fusionauth] token exchange failed (error_code=%s): %s",
            error_code,
            exc,
        )
        frontend = _validate_redirect_url(
            f"{cfg['frontend_url']}/auth?error={error_code}",
            cfg["allowed_redirects"],
        )
        return redirect(frontend)

    id_token = token_data.get("id_token", "")
    access_token = token_data.get("access_token", "")

    # Validate the ID token.
    jwks_uri = f"{cfg['base_url'].rstrip('/')}/.well-known/jwks.json"
    try:
        id_token_claims = validate_id_token(
            id_token=id_token,
            issuer=cfg["issuer"],
            client_id=cfg["client_id"],
            jwks_uri=jwks_uri,
        )
    except FusionAuthError as exc:
        logger.warning("[fusionauth] ID token validation failed: %s", exc)
        frontend = _validate_redirect_url(
            f"{cfg['frontend_url']}/auth?error=invalid_token",
            cfg["allowed_redirects"],
        )
        return redirect(frontend)

    # Optionally fetch UserInfo for additional profile data.
    userinfo_data = None
    if access_token:
        userinfo_data = get_userinfo(
            base_url=cfg["base_url"],
            access_token=access_token,
        )

    # Normalize the user profile.
    user = normalize_user(
        id_token_claims=id_token_claims,
        userinfo_data=userinfo_data,
    )

    # Redirect to the frontend and set the session cookie.
    frontend = _validate_redirect_url(
        cfg["frontend_url"],
        cfg["allowed_redirects"],
    )
    resp = redirect(frontend)
    _set_session_cookie(resp, user)
    # Clear the state cookie.
    resp.delete_cookie(
        "quien_auth_state",
        path="/",
        secure=cfg["cookie_secure"],
        samesite=cfg["cookie_samesite"],
        httponly=True,
    )
    return resp


@fusionauth_bp.route("/me", methods=["GET"])
def me():
    """Return the current authenticated user from the session cookie."""
    user = _get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated."}), 401
    # Ensure auth_provider is always present in the response.
    if "auth_provider" not in user:
        user["auth_provider"] = "google"
    return jsonify(user), 200


@fusionauth_bp.route("/logout", methods=["POST", "GET"])
def logout():
    """Clear the session cookie and optionally redirect to FusionAuth
    logout.

    For ``GET`` requests, redirects to FusionAuth's ``/oauth2/logout``
    endpoint to also end the FusionAuth session. For ``POST`` requests
    (called from the frontend via fetch), just clears the local cookie
    and returns JSON.
    """
    cfg = _get_config()

    if request.method == "GET":
        # Full logout: redirect to FusionAuth logout, which will
        # redirect back to the frontend.
        fa_logout = f"{cfg['base_url'].rstrip('/')}/oauth2/logout"
        frontend = _validate_redirect_url(
            cfg["frontend_url"], cfg["allowed_redirects"]
        )
        logout_url = (
            f"{fa_logout}?client_id={cfg['client_id']}"
            f"&post_logout_redirect_uri={frontend}"
        )
        resp = redirect(logout_url)
        _clear_session_cookie(resp)
        return resp

    # POST: just clear the local session cookie.
    resp = jsonify({"ok": True, "message": "Logged out."})
    _clear_session_cookie(resp)
    return resp


@fusionauth_bp.route("/config", methods=["GET"])
def config():
    """Return non-secret public auth config for the frontend."""
    cfg = _get_config()
    return jsonify({
        "configured": _is_configured(),
        "baseUrl": cfg["base_url"],
        "loginUrl": "/api/auth/login",
        "googleLoginUrl": "/api/auth/login/google",
        "logoutUrl": "/api/auth/logout",
        "meUrl": "/api/auth/me",
    }), 200


@fusionauth_bp.route("/debug", methods=["GET"])
def debug():
    """Development-only diagnostics. Never exposes secrets."""
    if current_app.config.get("ENV_NAME") == "production":
        return jsonify({
            "error": "Debug endpoint not available in production."
        }), 403

    cfg = _get_config()
    user = _get_current_user()
    return jsonify({
        "configured": _is_configured(),
        "baseUrl": cfg["base_url"],
        "issuer": cfg["issuer"],
        "clientId": cfg["client_id"][:8] + "..." if cfg["client_id"] else "",
        "redirectUri": cfg["redirect_uri"],
        "frontendUrl": cfg["frontend_url"],
        "cookieName": cfg["cookie_name"],
        "cookieSecure": cfg["cookie_secure"],
        "cookieSamesite": cfg["cookie_samesite"],
        "googleIdpId": cfg["google_idp_id"],
        "hasSession": user is not None,
        "userKeys": sorted(user.keys()) if user else [],
        "userEmail": user.get("email") if user else None,
        "userPicture": bool(user.get("picture")) if user else False,
        "authProvider": user.get("auth_provider") if user else None,
    }), 200

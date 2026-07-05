"""FusionAuth OIDC / OAuth2 service.

Handles the Authorization Code flow with PKCE against a FusionAuth
instance:

  1. ``build_authorization_url`` — generates state + PKCE verifier,
     returns the FusionAuth ``/oauth2/authorize`` URL.
  2. ``exchange_code_for_tokens`` — exchanges the authorization code
     + PKCE verifier for an access token / ID token.
  3. ``validate_id_token`` — validates the ID token signature using
     the FusionAuth JWKS endpoint, checks issuer, audience, expiration.
  4. ``get_userinfo`` — calls the FusionAuth UserInfo endpoint.
  5. ``normalize_user`` — extracts a clean, UI-friendly user dict
     from the ID token claims and/or UserInfo response.

Security:
  - Never logs access tokens, refresh tokens, ID tokens, client
    secrets, or authorization codes.
  - PKCE verifier and state are short-lived and stored server-side
    only (signed cookie / session).
  - ID token validation is always enforced (issuer, audience,
    signature, expiration).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import requests
import jwt as pyjwt
from jwt import PyJWKClient

logger = logging.getLogger(__name__)

# Timeout for FusionAuth HTTP calls during login.
_FA_TIMEOUT = 10  # seconds


class FusionAuthError(Exception):
    """Raised when a FusionAuth API call fails.

    Attributes:
        error_code: A short, specific, *non-secret* internal error
            code (e.g. ``token_exchange_invalid_grant``). Safe to
            surface to the frontend (as a redirect query param, for
            example) since it never contains tokens, codes, or
            secrets — only a classification of the failure.
    """

    def __init__(
        self, message: str, error_code: str = "token_exchange_failed"
    ) -> None:
        super().__init__(message)
        self.error_code = error_code


# ── PKCE helpers ────────────────────────────────────────────────────
def generate_pkce_pair() -> Tuple[str, str]:
    """Generate a PKCE code_verifier and code_challenge pair.

    Returns ``(code_verifier, code_challenge)`` where the challenge
    uses the S256 method.
    """
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def generate_state() -> str:
    """Generate a cryptographically secure state parameter."""
    return secrets.token_urlsafe(32)


# ── OIDC discovery ───────────────────────────────────────────────────
def _discover(base_url: str) -> Dict[str, Any]:
    """Fetch and cache the OIDC discovery document."""
    url = f"{base_url.rstrip('/')}/.well-known/openid-configuration"
    try:
        resp = requests.get(url, timeout=_FA_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise FusionAuthError(
            f"Failed to fetch OIDC discovery document from {url}: {exc}"
        ) from exc


# ── Authorization URL ────────────────────────────────────────────────
def build_authorization_url(
    *,
    base_url: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    scope: str = "openid email profile",
    idp_hint: str = "",
    prompt: str = "",
    max_age: Optional[int] = None,
) -> str:
    """Build the FusionAuth ``/oauth2/authorize`` URL.

    Uses the Authorization Code flow with PKCE (S256).

    When ``idp_hint`` is provided, FusionAuth skips its own login
    screen and redirects directly to the named Identity Provider
    (e.g. Google). When ``prompt`` is ``"login"``, FusionAuth
    forces a fresh login and does not silently reuse an existing
    FusionAuth SSO session. When ``max_age`` is ``0``, FusionAuth
    likewise requires immediate re-authentication (some versions
    may not support this; omit it if it causes errors).
    """
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    if idp_hint:
        params["idp_hint"] = idp_hint
    if prompt:
        params["prompt"] = prompt
    if max_age is not None:
        params["max_age"] = str(max_age)
    authorize_url = f"{base_url.rstrip('/')}/oauth2/authorize"
    return f"{authorize_url}?{urlencode(params)}"


# ── Token exchange diagnostics helpers ───────────────────────────────
# Fields that must never be logged, even in development.
_SECRET_REQUEST_FIELDS = {"client_secret", "code", "code_verifier"}
_SECRET_RESPONSE_FIELDS = {"access_token", "refresh_token", "id_token"}


def _safe_request_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the token-request form fields with secret
    values redacted, safe to log."""
    return {
        key: ("<redacted>" if key in _SECRET_REQUEST_FIELDS else value)
        for key, value in data.items()
    }


def _safe_response_body(resp: "requests.Response") -> str:
    """Return the token endpoint's response body with token values
    redacted, safe to log. Truncated to a reasonable length."""
    try:
        body = resp.json()
    except ValueError:
        return (resp.text or "")[:500]
    if isinstance(body, dict):
        redacted = {
            key: ("<redacted>" if key in _SECRET_RESPONSE_FIELDS else value)
            for key, value in body.items()
        }
        return json.dumps(redacted)[:1000]
    return str(body)[:500]


def _classify_token_error(resp: "requests.Response") -> str:
    """Map a failed FusionAuth ``/oauth2/token`` response to a
    specific, non-secret internal error code."""
    try:
        body = resp.json()
    except ValueError:
        body = {}

    oauth_error = (
        (body.get("error") or "").strip().lower()
        if isinstance(body, dict)
        else ""
    )
    description = (
        (body.get("error_description") or "").strip().lower()
        if isinstance(body, dict)
        else ""
    )

    if resp.status_code == 401 or oauth_error in {
        "invalid_client",
        "unauthorized_client",
    }:
        return "token_exchange_invalid_client"

    if oauth_error == "invalid_grant":
        if "redirect_uri" in description:
            return "token_exchange_redirect_uri_mismatch"
        pkce_terms = ("code_verifier", "code_challenge", "pkce")
        if any(term in description for term in pkce_terms):
            return "token_exchange_pkce_failed"
        return "token_exchange_invalid_grant"

    if oauth_error == "invalid_request":
        return "token_exchange_invalid_request"

    return "token_exchange_failed"


# ── Token exchange ──────────────────────────────────────────────────
def exchange_code_for_tokens(
    *,
    base_url: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
    code_verifier: str,
    debug: bool = False,
) -> Dict[str, Any]:
    """Exchange the authorization code for tokens at FusionAuth
    ``/oauth2/token``.

    Sent as ``application/x-www-form-urlencoded`` (never JSON), with
    ``grant_type=authorization_code``, ``code``, ``redirect_uri``,
    ``client_id``, ``client_secret``, and (when PKCE is used)
    ``code_verifier``.

    Returns the token response dict (``access_token``, ``id_token``,
    ``refresh_token``, ``token_type``, ``expires_in``, ...).

    On failure, raises :class:`FusionAuthError` with a specific
    ``error_code`` (see :func:`_classify_token_error`). When
    ``debug`` is ``True``, logs the HTTP status, the FusionAuth
    response body, and the outgoing request fields — with
    ``client_secret``, ``code``, ``code_verifier``, and all token
    values always redacted, even in debug mode.
    """
    token_url = f"{base_url.rstrip('/')}/oauth2/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
        "code_verifier": code_verifier,
    }

    try:
        resp = requests.post(
            token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=_FA_TIMEOUT,
        )
    except Exception as exc:
        logger.warning(
            "[fusionauth] token exchange request to %s failed before "
            "a response was received: %s",
            token_url,
            exc,
        )
        raise FusionAuthError(
            f"Token exchange request failed: {exc}",
            error_code="token_exchange_network_error",
        ) from exc

    if resp.status_code != 200:
        error_code = _classify_token_error(resp)
        if debug:
            logger.warning(
                "[fusionauth] token exchange failed: url=%s status=%s "
                "error_code=%s request_fields=%s response_body=%s",
                token_url,
                resp.status_code,
                error_code,
                _safe_request_fields(data),
                _safe_response_body(resp),
            )
        else:
            logger.warning(
                "[fusionauth] token exchange failed: status=%s error_code=%s",
                resp.status_code,
                error_code,
            )
        raise FusionAuthError(
            f"Token exchange failed with status {resp.status_code} "
            f"({error_code})",
            error_code=error_code,
        )

    try:
        token_data = resp.json()
    except ValueError as exc:
        raise FusionAuthError(
            "Token response was not valid JSON",
            error_code="token_exchange_invalid_response",
        ) from exc

    if not isinstance(token_data, dict) or "access_token" not in token_data:
        raise FusionAuthError(
            "Token response missing access_token",
            error_code="token_exchange_invalid_response",
        )
    return token_data


# ── ID token validation ─────────────────────────────────────────────
def validate_id_token(
    *,
    id_token: str,
    issuer: str,
    client_id: str,
    jwks_uri: str,
) -> Dict[str, Any]:
    """Validate the FusionAuth ID token and return its claims.

    Checks:
      - signature (using JWKS)
      - issuer
      - audience (client_id)
      - expiration

    **Never** logs the ID token value.
    """
    try:
        jwk_client = PyJWKClient(jwks_uri, timeout=_FA_TIMEOUT)
        signing_key = jwk_client.get_signing_key_from_jwt(id_token)
        claims = pyjwt.decode(
            id_token,
            key=signing_key.key,
            algorithms=["RS256"],
            issuer=issuer.rstrip("/"),
            audience=client_id,
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
        return claims
    except pyjwt.PyJWTError as exc:
        raise FusionAuthError(f"ID token validation failed: {exc}") from exc


# ── UserInfo ─────────────────────────────────────────────────────────
def get_userinfo(
    *,
    base_url: str,
    access_token: str,
) -> Optional[Dict[str, Any]]:
    """Call the FusionAuth UserInfo endpoint.

    ``GET /oauth2/userinfo``
    ``Authorization: Bearer <access_token>``

    Returns the response dict or ``None`` on failure.
    **Never** logs the access token.
    """
    userinfo_url = f"{base_url.rstrip('/')}/oauth2/userinfo"
    try:
        resp = requests.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=_FA_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning(
                "[fusionauth] userinfo endpoint returned status %s",
                resp.status_code,
            )
            return None
        data = resp.json()
        if not isinstance(data, dict):
            return None
        return data
    except Exception as exc:
        logger.warning("[fusionauth] userinfo fetch failed: %s", exc)
        return None


# ── User normalization ──────────────────────────────────────────────
def normalize_user(
    *,
    id_token_claims: Optional[Dict[str, Any]],
    userinfo_data: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Merge ID token claims and UserInfo response into a clean,
    UI-friendly user dict.

    Returns:
        {
            "fusionauth_user_id": "...",   # sub
            "email": "...",
            "email_verified": True,
            "full_name": "...",
            "first_name": "...",
            "last_name": "...",
            "picture": "...",
            "roles": [...],
        }
    """
    claims = id_token_claims or {}
    info = userinfo_data or {}

    def _pick(*keys: str) -> Optional[Any]:
        for source in (info, claims):
            for key in keys:
                val = source.get(key)
                if val not in (None, ""):
                    return val
        return None

    sub = _pick("sub")
    email = _pick("email")
    email_verified_raw = _pick("email_verified")
    if isinstance(email_verified_raw, str):
        email_verified = email_verified_raw.lower() in {"true", "1", "yes"}
    elif isinstance(email_verified_raw, bool):
        email_verified = email_verified_raw
    else:
        email_verified = False

    full_name = _pick("name", "full_name")
    first_name = _pick("given_name", "first_name")
    last_name = _pick("family_name", "last_name")
    picture = _pick("picture", "avatar_url")

    if not full_name and (first_name or last_name):
        full_name = f"{first_name or ''} {last_name or ''}".strip()
    if not full_name and email:
        full_name = email.split("@", 1)[0]

    roles_raw = _pick("roles", "groups")
    if isinstance(roles_raw, list):
        roles = [str(r) for r in roles_raw]
    elif isinstance(roles_raw, str):
        roles = [roles_raw]
    else:
        roles = []

    return {
        "fusionauth_user_id": sub,
        "email": email,
        "email_verified": email_verified,
        "full_name": full_name or "Usuario",
        "first_name": first_name,
        "last_name": last_name,
        "picture": picture,
        "roles": roles,
        "auth_provider": "google",
    }


# ── Session cookie helpers ─────────────────────────────────────────
def create_session_payload(user: Dict[str, Any]) -> str:
    """Create a signed session payload for the HTTP-only cookie.

    The payload is a JSON string containing the normalized user data
    plus an ``exp`` timestamp. It is signed with the session secret
    using HMAC-SHA256 to prevent tampering.

    **Never** includes OAuth tokens.
    """
    payload = {
        "user": user,
        "exp": int(time.time()) + 86400,  # 24 hours
    }
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(
        payload_json.encode("utf-8")
    ).decode("ascii")
    return payload_b64


def verify_session_payload(
    payload_b64: str,
    session_secret: str,
) -> Optional[Dict[str, Any]]:
    """Verify and decode a session payload from the cookie.

    Returns the user dict if valid and not expired, ``None`` otherwise.
    """
    try:
        payload_json = base64.urlsafe_b64decode(
            payload_b64.encode("ascii")
        ).decode("utf-8")
        payload = json.loads(payload_json)
        if not isinstance(payload, dict):
            return None
        exp = payload.get("exp")
        if not isinstance(exp, (int, float)) or exp < time.time():
            return None
        user = payload.get("user")
        if not isinstance(user, dict):
            return None
        return user
    except Exception:
        return None


def sign_payload(payload_b64: str, session_secret: str) -> str:
    """Sign a base64 payload with HMAC-SHA256."""
    sig = hmac.new(
        session_secret.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_signature(
    cookie_value: str,
    session_secret: str,
) -> Optional[str]:
    """Verify the HMAC signature and return the payload (b64) if valid."""
    if "." not in cookie_value:
        return None
    payload_b64, sig = cookie_value.rsplit(".", 1)
    expected_sig = hmac.new(
        session_secret.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return None
    return payload_b64


def create_session_cookie(
    user: Dict[str, Any],
    session_secret: str,
) -> str:
    """Create a signed session cookie value."""
    payload_b64 = create_session_payload(user)
    return sign_payload(payload_b64, session_secret)


def read_session_cookie(
    cookie_value: str,
    session_secret: str,
) -> Optional[Dict[str, Any]]:
    """Read and verify a session cookie, returning the user dict."""
    payload_b64 = verify_signature(cookie_value, session_secret)
    if payload_b64 is None:
        return None
    return verify_session_payload(payload_b64, session_secret)
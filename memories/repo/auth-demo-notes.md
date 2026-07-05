# auth-demo repo notes

## Stack
- Quien.uy auth demo migrated to **FusionAuth** (no more SuperTokens).
- Frontend: Vite 8 + React 19 + TypeScript on :5173.
- Backend: Flask on :5000 (single `backend/` folder, uses `backend/venv`).
- FusionAuth: :9011 (Docker), `API_KEY` env var. Uses Authorization Code + PKCE flow.

## Auth flow
- Frontend does **not** call FusionAuth or store OAuth tokens.
- Login button → `GET /api/auth/login` (Flask) → redirect to FusionAuth `/oauth2/authorize`.
- FusionAuth → `GET /api/auth/callback` (Flask) → exchanges code for tokens → validates ID token with `PyJWKClient` against FusionAuth JWKS → sets `URLSafeTimedSerializer`-signed HTTP-only session cookie → redirects to `FRONTEND_URL`.
- Frontend reads `/api/auth/me` for current user.
- Logout: `POST /api/auth/logout` clears the session cookie.

## Routing rule (do not break this)
- `vite.config.ts` has a **dev proxy** for `/api/*` → `http://localhost:5000`.
- In production, `nginx.conf` does the same routing.
- The login button uses `${VITE_AUTH_API_DOMAIN}/api/auth/login` (or relative `/api/auth/login` if the env var is unset, in which case the dev proxy takes over).
- `AppRouter.tsx` has a `*` catch-all that renders `NotFoundPage` — never put `/api/*` paths in React Router; they are network-level routes, not React routes.

## Backend key files
- `backend/app/api/fusionauth.py` — OIDC service: PKCE pair, state, authorization URL, token exchange, ID token validation, userinfo fetch, user normalization, session cookie creation/validation.
- `backend/app/api/auth_routes.py` — blueprint `fusionauth_bp` at `/api/auth` with routes `login`, `callback`, `me`, `logout`, `config`, `debug`.
- `backend/app/config.py` — FusionAuth config: `FUSIONAUTH_BASE_URL`, `FUSIONAUTH_ISSUER`, `FUSIONAUTH_CLIENT_ID`, `FUSIONAUTH_CLIENT_SECRET`, `FUSIONAUTH_REDIRECT_URI`, `FRONTEND_URL`, `AUTH_SESSION_SECRET`, `AUTH_COOKIE_NAME`, `AUTH_COOKIE_SECURE`, `AUTH_COOKIE_SAMESITE`, `AUTH_ALLOWED_REDIRECT_URLS`.
- `backend/app/__init__.py` — registers `fusionauth_bp` under `/api/auth` and exempts it from CSRF.

## Frontend key files
- `src/lib/auth.tsx` — `AuthProvider` + `useAuth` hook (no more SuperTokens). `login()` builds the backend URL from `VITE_AUTH_API_DOMAIN` (falls back to relative path).
- `src/api/client.ts` — axios with `baseURL = VITE_AUTH_API_DOMAIN` and `withCredentials: true`.
- `src/router/AppRouter.tsx` — React Router; the only `/api/*` paths are not React routes.
- `src/router/ProtectedRoute.tsx` — uses `useAuth()`.
- `src/types/index.ts` — `UserProfile` (alias of `AuthUser`) with `fusionauth_user_id`, `email`, `email_verified`, `full_name`, `first_name`, `last_name`, `picture`, `roles`.

## Dependencies
- `backend/requirements.txt` must include `itsdangerous==2.2.0` (used for the state-cookie serializer in `auth_routes.py`). It is a transitive dep of Flask but should be declared explicitly.
- `package.json` no longer has `supertokens-auth-react` or `supertokens-web-js`.
- `backend/app/api/fusionauth.py` requires `import hmac` — Flask/itsdangerous don't pull it in automatically when used directly. If you ever see `NameError: name 'hmac' is not defined` from the session-cookie helpers, that import is missing.
- Tested with **Python 3.14.3** on Windows: all packages in `backend/requirements.txt` install cleanly (`cryptography==45.0.5`, `PyJWT==2.10.1`, `Flask==3.1.2`, `mariadb==1.1.14`, etc.). The `create_app()` factory + all routes register without error.

## Environment variables
- Frontend (`/env`): `VITE_AUTH_API_DOMAIN=http://localhost:5000`, `VITE_WEBSITE_DOMAIN=http://localhost:5173`.
- Backend (`backend/example-env.txt`): full FusionAuth + cookie + CORS config.

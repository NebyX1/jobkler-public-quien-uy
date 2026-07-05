# Quien.uy — Auth Demo

Authentication demo for the Quien.uy project.

The frontend (this repo) is a React + Vite + TypeScript SPA that
delegates all authentication to a **Flask backend** using
**FusionAuth** as the identity provider via OAuth2 / OpenID Connect.

```
React/Vite frontend  ──►  Flask backend  ──►  FusionAuth  ──►  Google
   :5173                  :5000                :9011
```

## Architecture

- **Frontend** (Vite, port 5173): React SPA. Does NOT talk to Google
  directly. Does NOT store OAuth tokens. Uses a simple `AuthProvider`
  context that calls `/api/auth/me` to know the current user.
- **Backend** (Flask, port 5000): Handles the OAuth2 Authorization
  Code flow with PKCE against FusionAuth. Creates HTTP-only session
  cookies. Exposes `/api/auth/*` routes.
- **FusionAuth** (port 9011): Identity provider. Handles Google login,
  user management, OIDC tokens.

### Login flow

1. User clicks "Continuar con Google" on `/auth`.
2. Frontend navigates to `/api/auth/login` on the backend.
3. Backend generates state + PKCE verifier, redirects to FusionAuth
   `/oauth2/authorize`.
4. FusionAuth shows the Google login page.
5. User authenticates with Google.
6. FusionAuth redirects to the backend `/api/auth/callback` with an
   authorization code.
7. Backend exchanges the code for tokens, validates the ID token
   using the FusionAuth JWKS endpoint, normalizes the user profile.
8. Backend creates an HTTP-only session cookie and redirects to the
   frontend.
9. Frontend calls `/api/auth/me` to get the current user.
10. Frontend renders the authenticated UI (name, email, avatar).

## Repository layout

```
.
├── backend/              ← Flask backend (with FusionAuth auth routes)
│   ├── app/
│   │   ├── api/
│   │   │   ├── fusionauth.py     ← OIDC service module
│   │   │   ├── auth_routes.py    ← /api/auth/* routes
│   │   │   └── ...
│   │   ├── config.py             ← FusionAuth env vars
│   │   └── ...
│   ├── requirements.txt
│   └── example-env.txt
├── src/                  ← React/Vite frontend
│   ├── lib/auth.tsx              ← AuthProvider + useAuth hook
│   ├── lib/useUserProfile.ts     ← convenience profile hook
│   ├── pages/AuthPage.tsx        ← login page with Google button
│   ├── pages/DashboardPage.tsx   ← authenticated dashboard
│   ├── router/ProtectedRoute.tsx ← auth guard
│   ├── common/Navbar.tsx         ← navbar with avatar/logout
│   └── ...
├── .env.example          ← frontend env (VITE_AUTH_API_DOMAIN, …)
└── package.json
```

## Quick start (local)

### 0. Make sure FusionAuth is running

FusionAuth should be running at `http://localhost:9011`.

Verify:

```bash
curl http://localhost:9011/.well-known/openid-configuration
```

See the [FusionAuth setup](#fusionauth-setup) section below for
configuration details.

### 1. Run the backend

```bash
cd backend
cp example-env.txt .env
# edit .env and set:
#   FUSIONAUTH_CLIENT_ID=<your FusionAuth application client ID>
#   FUSIONAUTH_CLIENT_SECRET=<your FusionAuth application client secret>
#   AUTH_SESSION_SECRET=<a strong random secret>

pip install -r requirements.txt
python app.py              # http://localhost:5000
```

Verify:

```bash
curl http://localhost:5000/api/auth/config
curl -i http://localhost:5000/api/auth/me    # → 401 (expected)
```

### 2. Run the frontend

```bash
# from repo root
cp .env.example .env
# .env points to http://localhost:5000 / http://localhost:5173

npm install
npm run dev     # http://localhost:5173
```

Open <http://localhost:5173>. Any URL other than `/auth` redirects to
the login page.

### 3. Login

1. Open <http://localhost:5173/auth>.
2. Click "Continuar con Google".
3. You'll be redirected to FusionAuth, then to Google.
4. After Google login, you'll be redirected back to the frontend.
5. The dashboard shows your name, email, and avatar (if available).

## FusionAuth setup

### 1. Install FusionAuth

See the [FusionAuth documentation](https://fusionauth.io/docs/get-started)
for installation instructions. For local development, Docker is the
easiest option.

### 2. Create an Application

1. In FusionAuth, go to **Applications** → **Add Application**.
2. Name it (e.g. "Quien.uy Local").
3. Set the **Authorized redirect URL** to:
   ```
   http://localhost:5000/api/auth/callback
   ```
   (This is the backend callback, not the frontend.)
4. Note the **Client ID** and **Client Secret** — these go in the
   backend `.env` file.

### 3. Configure Google Identity Provider

1. In FusionAuth, go to **Identity Providers** → **Add Provider** →
   **Google**.
2. Set the Google Client ID and Client Secret from the
   [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
3. In Google Cloud Console, add the FusionAuth redirect URI:
   ```
   http://localhost:9011/oauth2/callback
   ```
4. Enable the Google provider for your Application.

### 4. Set environment variables

In `backend/.env`:

```
FUSIONAUTH_BASE_URL=http://localhost:9011
FUSIONAUTH_ISSUER=http://localhost:9011
FUSIONAUTH_CLIENT_ID=<your-client-id>
FUSIONAUTH_CLIENT_SECRET=<your-client-secret>
FUSIONAUTH_REDIRECT_URI=http://localhost:5000/api/auth/callback
FRONTEND_URL=http://localhost:5173
AUTH_SESSION_SECRET=<a-strong-random-secret>
AUTH_COOKIE_NAME=quien_session
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=Lax
AUTH_ALLOWED_REDIRECT_URLS=http://localhost:5173
```

## Backend API routes

| Method | Path                        | Auth    | Description                              |
|--------|-----------------------------|---------|------------------------------------------|
| GET    | `/api/auth/login`           | public  | Starts OAuth2 flow, redirects to FusionAuth |
| GET    | `/api/auth/callback`        | public  | Handles FusionAuth callback, creates session |
| GET    | `/api/auth/me`              | session | Returns current authenticated user      |
| POST   | `/api/auth/logout`          | public  | Clears session cookie                    |
| GET    | `/api/auth/config`          | public  | Returns non-secret auth config           |
| GET    | `/api/auth/debug`           | dev only| Development diagnostics                  |

## Security

- OAuth tokens are **never** stored in the frontend.
- OAuth tokens are used **only transiently** during the backend
  callback to fetch user info. They are not persisted.
- Session cookies are HTTP-only, Secure (in production), SameSite=Lax.
- ID tokens are validated: signature (JWKS), issuer, audience,
  expiration.
- State and PKCE verifier are stored in a short-lived signed cookie
  (10 min max age).
- No secrets are exposed to the frontend.
- No client secrets are committed to the repository.

## Production notes

For production:

- Set `AUTH_COOKIE_SECURE=true`.
- Use HTTPS for all URLs.
- Set `FUSIONAUTH_BASE_URL` to the public FusionAuth URL
  (e.g. `https://auth.quien.uy`).
- Set `FUSIONAUTH_REDIRECT_URI` to the public backend callback URL.
- Set `FRONTEND_URL` to the public frontend URL.
- Rotate `AUTH_SESSION_SECRET` regularly.
- The debug endpoint (`/api/auth/debug`) is disabled in production.

## Google Cloud Console notes

If you are migrating from a previous Google OAuth setup, update the
**Authorised redirect URI** in the Google Cloud Console to the
FusionAuth callback:

```
http://localhost:9011/oauth2/callback
```

The Google Client ID and Client Secret should be configured in
FusionAuth (not in the backend or frontend).

## Troubleshooting

- **FusionAuth not reachable**: `curl http://localhost:9011/.well-known/openid-configuration`
- **Login redirects fail**: Check `FUSIONAUTH_REDIRECT_URI` matches the
  FusionAuth Application's authorized redirect URL.
- **CORS errors**: Check `CORS_ORIGINS` in the backend includes
  `http://localhost:5173`.
- **Cookies not set**: Ensure `FRONTEND_URL` and `VITE_WEBSITE_DOMAIN`
  match the browser URL.
- **`/api/auth/me` returns 401**: The session cookie may be missing or
  expired. Log in again.
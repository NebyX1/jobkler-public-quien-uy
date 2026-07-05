import axios from 'axios';

/**
 * Axios client configured to talk to the backend.
 *
 * Authentication is handled via HTTP-only session cookies set by
 * the backend during the FusionAuth OAuth2 callback. We only need
 * to set `withCredentials: true` so the browser sends/receives
 * the session cookies cross-origin.
 *
 * We deliberately do NOT manually inject `Authorization: Bearer`
 * tokens. The backend uses cookie-based sessions, not header-based
 * tokens.
 */
const BASE_URL =
  (import.meta.env.VITE_AUTH_API_DOMAIN as string | undefined) ??
  'http://localhost:5000';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});
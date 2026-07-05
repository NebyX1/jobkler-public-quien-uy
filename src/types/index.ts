// ─── Auth (FusionAuth) ───────────────────────────────────────────────────────

/**
 * UI-friendly user returned by `GET /api/auth/me` on the backend.
 *
 * Built by the backend from FusionAuth ID token claims and the
 * UserInfo endpoint response. Never contains OAuth tokens.
 */
export interface UserProfile {
  fusionauth_user_id: string;
  email: string | null;
  email_verified: boolean;
  full_name: string;
  first_name: string | null;
  last_name: string | null;
  picture: string | null;
  roles: string[];
  auth_provider: string;
}

// ─── Auth (legacy backend) ───────────────────────────────────────────────────

export interface User {
  id: number;
  name: string;
  email: string;
  role: 'super_admin' | 'admin' | 'user';
  unit_id: number | null;
  unit_name: string | null;
  is_active: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  requires_2fa: boolean;
  pending_token: string;
}

export interface Verify2FARequest {
  code: string;
}

export interface Verify2FAResponse {
  access_token: string;
  user: User;
}

// ─── Books ────────────────────────────────────────────────────────────────────

export interface Book {
  id: number;
  title: string;
  author: string;
  isbn: string | null;
  genre: string | null;
  year: number | null;
  publisher: string | null;
  total_copies: number;
  available_copies: number;
  is_available: boolean;
  description: string | null;
  location: string | null;
  created_at: string;
  updated_at: string;
}

export interface BookFormData {
  title: string;
  author: string;
  isbn?: string;
  genre?: string;
  year?: number;
  publisher?: string;
  total_copies: number;
  available_copies?: number;
  description?: string;
  location?: string;
}

export interface BooksListResponse {
  items: Book[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export type AvailabilityFilter = 'all' | 'available' | 'unavailable';

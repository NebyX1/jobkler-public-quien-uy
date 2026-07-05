import { useAuth } from './auth';

/**
 * Re-export the auth user type and the initials helper for
 * backwards compatibility with components that previously imported
 * from this module.
 */
export type { AuthUser as UserProfile } from './auth';

/**
 * Derive 1–2 character initials from a display name for the
 * fallback avatar. Falls back to '?' when the name is empty.
 *
 * Examples:
 *   "Ada Lovelace"  -> "AL"
 *   "Ada"           -> "A"
 *   "ada"           -> "A"
 *   ""              -> "?"
 */
export function initialsFromName(name: string | null | undefined): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) {
    return parts[0]!.slice(0, 1).toUpperCase();
  }
  return (parts[0]!.slice(0, 1) + parts[parts.length - 1]!.slice(0, 1))
    .toUpperCase();
}

/**
 * Convenience hook that returns the current authenticated user
 * from the AuthProvider context.
 */
export function useUserProfile() {
  const { user, loading, refresh } = useAuth();
  return {
    data: user,
    isLoading: loading,
    isError: false,
    refetch: refresh,
  };
}

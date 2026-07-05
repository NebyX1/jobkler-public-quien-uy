import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../types';

interface AuthState {
  token: string | null;
  pendingToken: string | null;
  user: User | null;
  setToken: (token: string, user: User) => void;
  setPendingToken: (token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      pendingToken: null,
      user: null,

      setToken: (token, user) =>
        set({ token, user, pendingToken: null }),

      setPendingToken: (token) =>
        set({ pendingToken: token }),

      logout: () =>
        set({ token: null, pendingToken: null, user: null }),
    }),
    {
      name: 'auth-storage',
      // Solo persiste token y user, no pendingToken
      partialize: (state) => ({ token: state.token, user: state.user }),
    }
  )
);

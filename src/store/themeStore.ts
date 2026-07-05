import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Theme = 'quienLight' | 'quienDark';

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

function getInitialTheme(): Theme {
  if (typeof window === 'undefined') return 'quienLight';
  const saved = localStorage.getItem('quien-theme');
  if (saved === 'quienLight' || saved === 'quienDark') return saved;
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'quienDark';
  }
  return 'quienLight';
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: getInitialTheme(),
      setTheme: (theme) => set({ theme }),
      toggleTheme: () =>
        set({
          theme: get().theme === 'quienLight' ? 'quienDark' : 'quienLight',
        }),
    }),
    { name: 'quien-theme' }
  )
);

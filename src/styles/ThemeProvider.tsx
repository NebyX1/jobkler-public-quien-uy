import { useEffect, type ReactNode } from 'react';
import { useThemeStore } from '../store/themeStore';

/**
 * ThemeProvider for Quien.uy.
 *
 * Syncs the DaisyUI theme attribute on <html> with the persisted
 * theme from the Zustand store. On first load, the store respects
 * the saved preference or the system color-scheme preference.
 */
interface ThemeProviderProps {
  children: ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const theme = useThemeStore((s) => s.theme);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  return <>{children}</>;
}

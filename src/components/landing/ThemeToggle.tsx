import { Sun, Moon } from 'lucide-react';
import { useThemeStore } from '../../store/themeStore';

/**
 * Theme toggle button for switching between light and dark mode.
 * Uses the persisted Zustand store and syncs via ThemeProvider.
 */
export function ThemeToggle() {
  const { theme, toggleTheme } = useThemeStore();
  const isDark = theme === 'quienDark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="btn btn-ghost btn-circle btn-sm border-0 text-base-content/70 hover:bg-base-200 hover:text-primary"
      aria-label={isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
      title={isDark ? 'Modo claro' : 'Modo oscuro'}
    >
      {isDark ? (
        <Sun className="h-5 w-5" aria-hidden="true" />
      ) : (
        <Moon className="h-5 w-5" aria-hidden="true" />
      )}
    </button>
  );
}
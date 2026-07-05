/**
 * Footer for the authenticated app layout.
 * Uses Tailwind/DaisyUI classes instead of Fluent UI.
 */
export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-base-300 bg-base-200 px-6 py-4 text-center">
      <p className="text-xs text-base-content/50">
        © {year} Quien.uy · Directorio local de profesionales y servicios
      </p>
    </footer>
  );
}

import { Outlet } from 'react-router-dom';
import { Navbar } from '../components/landing/Navbar';
import { Footer } from '../components/landing/Footer';

/**
 * Shared layout for protected routes.
 * Uses the unified Navbar that adapts based on auth state.
 */
export function MainLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-base-100">
      <Navbar />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}

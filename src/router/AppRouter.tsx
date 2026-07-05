import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from './ProtectedRoute';
import { MainLayout } from '../common/MainLayout';
import { LandingPage } from '../pages/landing/LandingPage';
import { AuthPage } from '../pages/AuthPage';
import { DashboardPage } from '../pages/DashboardPage';
import { NotFoundPage } from '../pages/NotFoundPage';
import { SearchResultsPage } from '../pages/SearchResultsPage';
import { NearMePage } from '../pages/NearMePage';
import { ProfileDetailPage } from '../pages/ProfileDetailPage';

/**
 * Top-level router.
 *
 * Public routes:
 *   /           – Landing page (Quien.uy)
 *   /buscar      – Search results (query params: q, departamento, localidad)
 *   /auth        – Login page (FusionAuth redirect button)
 *   /auth/callback – Loading state after backend callback redirect
 *
 * Protected routes:
 *   /dashboard  – Dashboard (shows session info + logout)
 *
 * Any unauthenticated user typing a protected URL is redirected
 * to /auth by <ProtectedRoute>.
 */
export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public: landing page */}
        <Route path="/" element={<LandingPage />} />

        {/* Public: search results */}
        <Route path="/buscar" element={<SearchResultsPage />} />
        <Route path="/buscar/:department" element={<SearchResultsPage />} />
        <Route path="/buscar/:department/:locality" element={<SearchResultsPage />} />
        <Route path="/cerca-de-mi" element={<NearMePage />} />
        <Route path="/perfil/:slug" element={<ProfileDetailPage />} />

        {/* Public: login page + callback loading state */}
        <Route path="/auth/*" element={<AuthPage />} />

        {/* Protected – with the shared layout */}
        <Route
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/catalog" element={<Navigate to="/dashboard" replace />} />
          <Route path="/catalog/*" element={<Navigate to="/dashboard" replace />} />
        </Route>

        {/* 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}

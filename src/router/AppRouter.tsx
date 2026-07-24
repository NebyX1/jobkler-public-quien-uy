import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from './ProtectedRoute';
import { MainLayout } from '../common/MainLayout';
import { LandingPage } from '../pages/landing/LandingPage';
import { AuthPage } from '../pages/AuthPage';
import { LoginPage } from '../pages/LoginPage';
import { MyAccountPage } from '../pages/MyAccountPage';
import { MyProfilePage } from '../pages/MyProfilePage';
import { ProfileFormPage } from '../pages/ProfileFormPage';
import { MyReviewsPage } from '../pages/MyReviewsPage';
import { LoginRequiredPage } from '../pages/LoginRequiredPage';
import { NotFoundPage } from '../pages/NotFoundPage';
import { SearchResultsPage } from '../pages/SearchResultsPage';
import { NearMePage } from '../pages/NearMePage';
import { ProfileDetailPage } from '../pages/ProfileDetailPage';

/**
 * Top-level router.
 *
 * Public routes:
 *   /                  – Landing page
 *   /buscar            – Search results
 *   /buscar/:dept      – Search filtered by department
 *   /buscar/:dept/:loc – Search filtered by dept + locality
 *   /cerca-de-mi       – Location-based suggestions
 *   /perfil/:slug      – Public profile detail
 *   /login             – Login page (explicit Google button, no auto-OAuth)
 *   /auth/*            – OAuth callback handler
 *   /login-required    – Legacy redirect to /login
 *
 * Protected routes (require authentication):
 *   /mi-cuenta         – Account page
 *   /mi-perfil         – Profile owner dashboard
 *   /mi-perfil/crear   – Create profile
 *   /mi-perfil/editar  – Edit profile
 *   /mis-reviews       – Reviews written by user
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

        {/* Public: login page + OAuth callback */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/*" element={<AuthPage />} />
        <Route path="/login-required" element={<LoginRequiredPage />} />

        {/* Protected – with the shared layout */}
        <Route
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/mi-cuenta" element={<MyAccountPage />} />
          <Route path="/mi-perfil" element={<MyProfilePage />} />
          <Route path="/mi-perfil/crear" element={<ProfileFormPage />} />
          <Route path="/mi-perfil/editar" element={<ProfileFormPage />} />
          <Route path="/mis-reviews" element={<MyReviewsPage />} />
        </Route>

        {/* Legacy redirects */}
        <Route path="/dashboard" element={<Navigate to="/mi-cuenta" replace />} />
        <Route path="/catalog" element={<Navigate to="/mi-cuenta" replace />} />
        <Route path="/catalog/*" element={<Navigate to="/mi-cuenta" replace />} />

        {/* 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}

import { Link } from 'react-router-dom';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import {
  FileText,
  Plus,
  Eye,
  Pencil,
  Trash2,
  Power,
  Star,
  BadgeCheck,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { useAuth } from '../lib/auth';
import {
  getProfileByOwnerUserId,
  deactivateOwnedProfile,
  deleteOwnedProfile,
} from '../services/profileService';
import { ProfileAvatar } from '../components/ProfileAvatar';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { useState } from 'react';
import type { Profile } from '../types/profile';

/**
 * My Profile page — owner dashboard for the authenticated user's
 * professional profile.
 *
 * Covers all required states:
 *  1. Loading the user's profile.
 *  2. User does not have a profile yet (empty state, not an error).
 *  3. User already has a profile (full management dashboard).
 *  4. Real loading or network error (with retry).
 *  5. Profile deletion in progress (loading state).
 *  6. Successful deletion (confirmation message).
 *  7. Retry after an error.
 */
export function MyProfilePage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const userId = user?.fusionauth_user_id ?? null;

  const [showDeactivate, setShowDeactivate] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const {
    data: profile,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery<Profile | null, Error>({
    queryKey: ['my-profile', userId],
    queryFn: () =>
      userId ? getProfileByOwnerUserId(userId) : Promise.resolve(null),
    enabled: Boolean(userId),
  });

  // Deactivate / reactivate mutation
  const deactivateMutation = useMutation({
    mutationFn: () => {
      if (!profile || !userId) {
        return Promise.reject(new Error('No hay perfil para desactivar.'));
      }
      return deactivateOwnedProfile(profile.id, userId);
    },
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['my-profile'] });
      setShowDeactivate(false);
      setActionError(null);
      setActionSuccess(
        updated.status === 'inactive'
          ? 'Perfil desactivado. Ya no aparece en las búsquedas.'
          : 'Perfil reactivado. Vuelve a aparecer en las búsquedas.',
      );
    },
    onError: (err) => {
      setActionError(
        err instanceof Error ? err.message : 'Error al desactivar el perfil.',
      );
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => {
      if (!profile || !userId) {
        return Promise.reject(new Error('No hay perfil para eliminar.'));
      }
      return deleteOwnedProfile(profile.id, userId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-profile'] });
      queryClient.invalidateQueries({ queryKey: ['profile-detail'] });
      setShowDelete(false);
      setActionError(null);
      setActionSuccess('Perfil eliminado correctamente.');
    },
    onError: (err) => {
      setActionError(
        err instanceof Error ? err.message : 'Error al eliminar el perfil.',
      );
    },
  });

  const handleDeactivate = () => {
    setActionError(null);
    setActionSuccess(null);
    deactivateMutation.mutate();
  };

  const handleDelete = () => {
    setActionError(null);
    setActionSuccess(null);
    deleteMutation.mutate();
  };

  const handleRetry = () => {
    setActionError(null);
    void refetch();
  };

  const isActionPending = deactivateMutation.isPending || deleteMutation.isPending;
  const isDeleting = deleteMutation.isPending;

  // ── State 1: Loading ──────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-extrabold text-base-content">Mi perfil</h1>
        </div>
        <div className="rounded-[2rem] border border-base-300/70 bg-base-200/50 p-8 shadow-sm sm:p-10">
          <div className="flex flex-col items-center gap-4">
            <span className="loading loading-spinner loading-lg text-primary" />
            <p className="text-sm text-base-content/60">Cargando tu perfil…</p>
          </div>
        </div>
      </div>
    );
  }

  // ── State 4: Error (with retry) ──────────────────────────────────
  if (isError) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-extrabold text-base-content">Mi perfil</h1>
        </div>
        <div className="rounded-[2rem] border border-error/20 bg-error/5 p-8 text-center shadow-sm sm:p-10">
          <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-error/10">
            <AlertCircle className="h-7 w-7 text-error" />
          </div>
          <h2 className="text-xl font-bold text-base-content">
            No pudimos cargar tu perfil
          </h2>
          <p className="mt-2 max-w-md mx-auto text-sm text-base-content/70">
            Hubo un problema de conexión con el servidor.
            {error?.message ? ` (${error.message})` : ''}
          </p>
          <button
            onClick={handleRetry}
            disabled={isFetching}
            className="btn btn-primary mt-6 rounded-full"
          >
            {isFetching ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            {isFetching ? 'Reintentando…' : 'Reintentar'}
          </button>
        </div>
      </div>
    );
  }

  // ── State 2: No profile yet (empty state) ─────────────────────────
  if (!profile) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-extrabold text-base-content">Mi perfil</h1>
        </div>

        {actionSuccess && (
          <div className="rounded-2xl border border-success/20 bg-success/5 p-4 text-sm text-success">
            <CheckCircle2 className="mr-2 inline h-4 w-4" />
            {actionSuccess}
          </div>
        )}

        <div className="rounded-[2rem] border border-base-300/70 bg-base-200/50 p-8 text-center shadow-sm sm:p-12">
          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <FileText className="h-8 w-8 text-primary" />
          </div>
          <h2 className="text-xl font-bold text-base-content">
            Todavía no creaste tu perfil en Quien.uy
          </h2>
          <p className="mt-3 max-w-md mx-auto text-sm text-base-content/70">
            Creá tu perfil profesional para que personas de tu zona puedan
            encontrarte y contactarte.
          </p>
          <Link
            to="/mi-perfil/crear"
            className="btn btn-primary mt-6 rounded-full"
          >
            <Plus className="h-4 w-4" />
            Crear mi perfil
          </Link>
        </div>
      </div>
    );
  }

  // ── States 3, 5, 6: Has profile ───────────────────────────────────
  const isInactive = profile.status === 'inactive';

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-extrabold text-base-content">Mi perfil</h1>
        <p className="mt-1 text-sm text-base-content/60">
          Gestioná tu perfil profesional público.
        </p>
      </div>

      {actionError && (
        <div className="rounded-2xl border border-error/20 bg-error/10 p-4 text-sm text-error">
          <AlertCircle className="mr-2 inline h-4 w-4" />
          {actionError}
          <button
            onClick={() => setActionError(null)}
            className="ml-2 underline"
          >
            Cerrar
          </button>
        </div>
      )}

      {actionSuccess && (
        <div className="rounded-2xl border border-success/20 bg-success/5 p-4 text-sm text-success">
          <CheckCircle2 className="mr-2 inline h-4 w-4" />
          {actionSuccess}
          <button
            onClick={() => setActionSuccess(null)}
            className="ml-2 underline"
          >
            Cerrar
          </button>
        </div>
      )}

      {isInactive && (
        <div className="rounded-2xl border border-warning/30 bg-warning/10 p-4 text-sm text-base-content">
          Tu perfil está <strong>desactivado</strong> y no aparece en las búsquedas.
          Podés reactivarlo editándolo.
        </div>
      )}

      {/* State 5: Deleting in progress — overlay banner */}
      {isDeleting && (
        <div className="rounded-2xl border border-error/30 bg-error/5 p-4 text-sm text-base-content">
          <Loader2 className="mr-2 inline h-4 w-4 animate-spin text-error" />
          Eliminando tu perfil…
        </div>
      )}

      {/* Profile preview card */}
      <div className="rounded-[2rem] border border-base-300/70 bg-base-200/50 p-6 shadow-sm sm:p-8">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
          <ProfileAvatar
            src={profile.photoUrl}
            fallbackSrc={profile.avatarFallback}
            name={profile.displayName || profile.name}
            size={80}
          />
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-2xl font-extrabold text-base-content">
                {profile.displayName || profile.name}
              </h2>
              {profile.verified && (
                <span className="badge badge-lg gap-1 rounded-full border-0 bg-primary/10 text-primary">
                  <BadgeCheck className="h-4 w-4" />
                  Verificado
                </span>
              )}
              {isInactive && (
                <span className="badge badge-lg rounded-full border-0 bg-warning/10 text-warning">
                  Desactivado
                </span>
              )}
            </div>
            <p className="mt-1 text-base-content/70">
              {profile.profession} · {profile.category}
            </p>
            <p className="text-sm text-base-content/60">
              {profile.locality}, {profile.department}
            </p>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="badge rounded-full border-0 bg-primary/10 text-primary">
                {profile.availability || 'Disponible'}
              </span>
              <span className="badge rounded-full border-0 bg-base-100 text-base-content/70">
                <Star className="mr-1 h-3.5 w-3.5 text-warning" />
                {profile.rating?.toFixed(1) ?? '0.0'} · {profile.reviewsCount ?? 0} reseñas
              </span>
            </div>
          </div>
        </div>

        <p className="mt-5 text-sm leading-relaxed text-base-content/70">
          {profile.shortDescription}
        </p>

        {profile.tags?.length ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {profile.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-base-300/70 bg-base-100 px-3 py-1 text-xs font-medium text-base-content/70"
              >
                {tag}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        <Link
          to={`/perfil/${profile.slug}`}
          className="btn btn-outline btn-sm rounded-full border-base-300 text-base-content"
        >
          <Eye className="h-4 w-4" />
          Ver perfil público
        </Link>
        <Link
          to="/mi-perfil/editar"
          className="btn btn-primary btn-sm rounded-full"
        >
          <Pencil className="h-4 w-4" />
          Editar perfil
        </Link>
        <button
          onClick={() => setShowDeactivate(true)}
          disabled={isActionPending}
          className="btn btn-ghost btn-sm rounded-full text-base-content/60 hover:text-warning disabled:opacity-50"
        >
          <Power className="h-4 w-4" />
          {isInactive ? 'Reactivar' : 'Desactivar'}
        </button>
        <button
          onClick={() => setShowDelete(true)}
          disabled={isActionPending}
          className="btn btn-ghost btn-sm rounded-full text-base-content/60 hover:text-error disabled:opacity-50"
        >
          <Trash2 className="h-4 w-4" />
          Eliminar
        </button>
      </div>

      {/* Contact info */}
      <div className="max-w-lg rounded-[1.5rem] border border-base-300/70 bg-base-100 p-6 shadow-sm">
        <h3 className="text-lg font-bold text-base-content">Información de contacto</h3>
        <div className="mt-3 space-y-2 text-sm text-base-content/70">
          {profile.phone && (
            <p><span className="font-semibold text-base-content">Tel:</span> {profile.phone}</p>
          )}
          {profile.whatsapp && (
            <p><span className="font-semibold text-base-content">WhatsApp:</span> {profile.whatsapp}</p>
          )}
          {profile.email && (
            <p><span className="font-semibold text-base-content">Email:</span> {profile.email}</p>
          )}
          {profile.website && (
            <p>
              <span className="font-semibold text-base-content">Sitio:</span>{' '}
              <a className="link link-primary" href={profile.website} target="_blank" rel="noreferrer">
                {profile.website}
              </a>
            </p>
          )}
          {profile.instagram && (
            <p>
              <span className="font-semibold text-base-content">Instagram:</span>{' '}
              <a className="link link-primary" href={profile.instagram} target="_blank" rel="noreferrer">
                {profile.instagram}
              </a>
            </p>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={showDeactivate}
        title={isInactive ? 'Reactivar perfil' : 'Desactivar perfil'}
        message={
          isInactive
            ? '¿Querés reactivar tu perfil? Volverá a aparecer en las búsquedas.'
            : '¿Querés desactivar tu perfil? No aparecerá en las búsquedas pero tus datos se conservan.'
        }
        confirmLabel={isInactive ? 'Reactivar' : 'Desactivar'}
        onConfirm={handleDeactivate}
        onCancel={() => setShowDeactivate(false)}
        danger={!isInactive}
      />

      <ConfirmDialog
        open={showDelete}
        title="Eliminar perfil"
        message="¿Estás seguro de que querés eliminar tu perfil? Esta acción no se puede deshacer. Se borrarán todos los datos del perfil."
        confirmLabel="Eliminar"
        onConfirm={handleDelete}
        onCancel={() => setShowDelete(false)}
        danger
      />
    </div>
  );
}

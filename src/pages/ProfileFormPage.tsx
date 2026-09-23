import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../lib/auth';
import {
  getProfileByOwnerUserId,
  createProfileForUser,
  updateOwnedProfile,
} from '../services/profileService';
import { ProfileForm, type ProfileFormValues } from '../components/profiles/ProfileForm';
import { useState } from 'react';
import type { Profile } from '../types/profile';

/**
 * Profile create/edit page.
 * Routes: /mi-perfil/crear, /mi-perfil/editar
 */
export function ProfileFormPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isEdit = window.location.pathname.includes('/editar');

  const { data: existingProfile, isLoading } = useQuery({
    queryKey: ['my-profile', user?.fusionauth_user_id],
    queryFn: () => getProfileByOwnerUserId(),
    enabled: isEdit && Boolean(user?.fusionauth_user_id),
  });

  // If creating, check if profile already exists
  const { data: existingForCreate, isLoading: checkingCreate } = useQuery({
    queryKey: ['my-profile-check', user?.fusionauth_user_id],
    queryFn: () => getProfileByOwnerUserId(),
    enabled: !isEdit && Boolean(user?.fusionauth_user_id),
  });

  const handleSubmit = async (values: ProfileFormValues) => {
    if (!user || isSubmitting) return;
    setSubmitError(null);
    setIsSubmitting(true);

    try {
      const serviceArea = values.serviceArea
        ? values.serviceArea.split(',').map((s) => s.trim()).filter(Boolean)
        : [];
      const tags = values.tags
        ? values.tags.split(',').map((s) => s.trim()).filter(Boolean)
        : [];

      const profileInput = {
        displayName: values.displayName,
        categoryId: values.categoryId,
        profession: values.profession,
        shortDescription: values.shortDescription,
        description: values.description,
        photoUrl: values.photoUrl || '',
        phone: values.phone || '',
        whatsapp: values.whatsapp || '',
        email: values.email || '',
        website: values.website || '',
        instagram: values.instagram || '',
        department: values.department,
        departmentId: values.department.toLowerCase().replace(/\s+/g, '-'),
        locality: values.locality,
        localityId: values.locality.toLowerCase().replace(/\s+/g, '-'),
        address: values.address || '',
        serviceArea,
        tags,
        availability: values.availability || 'Disponible',
        yearsExperience: values.yearsExperience || 0,
      };

      if (isEdit && existingProfile) {
        await updateOwnedProfile(existingProfile.id, profileInput as Partial<Profile>);
      } else {
        await createProfileForUser(profileInput as Parameters<typeof createProfileForUser>[0]);
      }

      queryClient.invalidateQueries({ queryKey: ['my-profile'] });
      navigate('/mi-perfil');
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Error al guardar el perfil.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading || checkingCreate) {
    return (
      <div className="flex flex-col gap-6">
        <div className="skeleton h-8 w-48 rounded-full" />
        <div className="skeleton h-64 w-full rounded-[2rem]" />
      </div>
    );
  }

  // If editing but no profile exists, redirect to create
  if (isEdit && !existingProfile) {
    navigate('/mi-perfil/crear', { replace: true });
    return null;
  }

  // If creating but profile already exists, redirect to edit
  if (!isEdit && existingForCreate) {
    navigate('/mi-perfil/editar', { replace: true });
    return null;
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-extrabold text-base-content">
          {isEdit ? 'Editar perfil' : 'Crear perfil'}
        </h1>
        <p className="mt-1 text-sm text-base-content/60">
          {isEdit
            ? 'Modificá la información de tu perfil profesional.'
            : 'Completá los datos para crear tu perfil profesional en Quien.uy.'}
        </p>
      </div>

      {submitError && (
        <div className="rounded-2xl border border-error/20 bg-error/10 p-4 text-sm text-error">
          {submitError}
          <button onClick={() => setSubmitError(null)} className="ml-2 underline">
            Cerrar
          </button>
        </div>
      )}

      <ProfileForm
        initialData={isEdit ? existingProfile : null}
        onSubmit={handleSubmit}
        onCancel={() => navigate('/mi-perfil')}
        isEditing={isEdit}
        isSubmitting={isSubmitting}
      />
    </div>
  );
}

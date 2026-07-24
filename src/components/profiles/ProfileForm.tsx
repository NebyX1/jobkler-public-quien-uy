import { useEffect, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Save, X } from 'lucide-react';
import { uruguayLocations, departmentList } from '../../data/uruguayLocations';
import type { Profile } from '../../types/profile';

const CATEGORIES = [
  { id: 'profesionales', name: 'Profesionales' },
  { id: 'oficios', name: 'Oficios' },
  { id: 'bienestar-y-salud', name: 'Bienestar y salud' },
  { id: 'belleza', name: 'Belleza' },
  { id: 'hogar', name: 'Hogar' },
  { id: 'tecnologia', name: 'Tecnología' },
  { id: 'educacion', name: 'Educación' },
  { id: 'espiritualidad', name: 'Espiritualidad' },
  { id: 'eventos', name: 'Eventos' },
  { id: 'servicios-rurales', name: 'Servicios rurales' },
];

const profileSchema = z.object({
  displayName: z.string().min(2, 'El nombre debe tener al menos 2 caracteres.'),
  categoryId: z.string().min(1, 'Seleccioná una categoría.'),
  profession: z.string().min(2, 'Ingresá tu profesión u oficio.'),
  shortDescription: z.string().min(10, 'Mínimo 10 caracteres.').max(160, 'Máximo 160 caracteres.'),
  description: z.string().min(20, 'Mínimo 20 caracteres.').max(1000, 'Máximo 1000 caracteres.'),
  photoUrl: z.string().url('URL inválida.').optional().or(z.literal('')),
  phone: z.string().optional().or(z.literal('')),
  whatsapp: z.string().optional().or(z.literal('')),
  email: z.string().email('Email inválido.').optional().or(z.literal('')),
  website: z.string().url('URL inválida.').optional().or(z.literal('')),
  instagram: z.string().url('URL inválida.').optional().or(z.literal('')),
  department: z.string().min(1, 'Seleccioná un departamento.'),
  locality: z.string().min(1, 'Seleccioná una localidad.'),
  address: z.string().optional().or(z.literal('')),
  serviceArea: z.string().optional().or(z.literal('')),
  tags: z.string().optional().or(z.literal('')),
  availability: z.string().optional().or(z.literal('')),
  yearsExperience: z.number().min(0).optional(),
}).refine(
  (data) => data.phone || data.whatsapp || data.email,
  { message: 'Ingresá al menos un medio de contacto (teléfono, WhatsApp o email).', path: ['phone'] },
);

export type ProfileFormValues = z.infer<typeof profileSchema>;

interface ProfileFormProps {
  initialData?: Profile | null;
  onSubmit: (values: ProfileFormValues) => Promise<void>;
  onCancel: () => void;
  isEditing?: boolean;
  isSubmitting?: boolean;
}

function getCategoryIdByName(name: string): string {
  return CATEGORIES.find((c) => c.name === name)?.id || '';
}

/**
 * Profile create/edit form.
 * Uses react-hook-form + zod for validation.
 * Department/locality uses the same dependent select pattern as SearchPanel.
 */
export function ProfileForm({
  initialData,
  onSubmit,
  onCancel,
  isEditing = false,
  isSubmitting = false,
}: ProfileFormProps) {
  const defaultValues = useMemo<Partial<ProfileFormValues>>(() => {
    if (!initialData) {
      return {
        displayName: '',
        categoryId: '',
        profession: '',
        shortDescription: '',
        description: '',
        photoUrl: '',
        phone: '',
        whatsapp: '',
        email: '',
        website: '',
        instagram: '',
        department: '',
        locality: '',
        address: '',
        serviceArea: '',
        tags: '',
        availability: '',
        yearsExperience: 0,
      };
    }
    return {
      displayName: initialData.displayName || initialData.name,
      categoryId: initialData.categoryId || getCategoryIdByName(initialData.category),
      profession: initialData.profession,
      shortDescription: initialData.shortDescription,
      description: initialData.description,
      photoUrl: initialData.photoUrl || '',
      phone: initialData.phone || '',
      whatsapp: initialData.whatsapp || '',
      email: initialData.email || '',
      website: initialData.website || '',
      instagram: initialData.instagram || '',
      department: initialData.department,
      locality: initialData.locality,
      address: initialData.address || '',
      serviceArea: initialData.serviceArea?.join(', ') || '',
      tags: initialData.tags?.join(', ') || '',
      availability: initialData.availability || '',
      yearsExperience: initialData.yearsExperience || 0,
    };
  }, [initialData]);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues,
  });

  const selectedDepartment = watch('department');
  const localities = useMemo(
    () => (selectedDepartment ? uruguayLocations[selectedDepartment] ?? [] : []),
    [selectedDepartment],
  );

  // Reset locality when department changes
  useEffect(() => {
    const sub = watch((_value, { name }) => {
      if (name === 'department') {
        setValue('locality', '', { shouldValidate: false });
      }
    });
    return () => sub.unsubscribe();
  }, [watch, setValue]);

  const fieldClasses =
    'h-12 w-full rounded-2xl border border-base-300/70 bg-base-100 px-4 text-sm text-base-content placeholder:text-base-content/40 transition focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/35';
  const labelClasses =
    'mb-2 block text-xs font-semibold uppercase tracking-wide text-base-content/60';
  const errorClasses = 'mt-1 text-xs text-error';

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
      {/* Basic info */}
      <section className="rounded-[2rem] border border-base-300/70 bg-base-200/50 p-6 shadow-sm sm:p-8">
        <h2 className="text-lg font-bold text-base-content">Información básica</h2>
        <div className="mt-5 grid gap-5 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label htmlFor="displayName" className={labelClasses}>Nombre profesional *</label>
            <input id="displayName" {...register('displayName')} className={fieldClasses} placeholder="Ej: Ana Ferreira" />
            {errors.displayName && <p className={errorClasses}>{errors.displayName.message}</p>}
          </div>

          <div>
            <label htmlFor="categoryId" className={labelClasses}>Categoría *</label>
            <select id="categoryId" {...register('categoryId')} className={fieldClasses}>
              <option value="">Seleccionar categoría</option>
              {CATEGORIES.map((cat) => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
            {errors.categoryId && <p className={errorClasses}>{errors.categoryId.message}</p>}
          </div>

          <div>
            <label htmlFor="profession" className={labelClasses}>Profesión u oficio *</label>
            <input id="profession" {...register('profession')} className={fieldClasses} placeholder="Ej: Psicóloga" />
            {errors.profession && <p className={errorClasses}>{errors.profession.message}</p>}
          </div>

          <div className="sm:col-span-2">
            <label htmlFor="shortDescription" className={labelClasses}>Descripción corta *</label>
            <input id="shortDescription" {...register('shortDescription')} className={fieldClasses} placeholder="Resumen en una línea" maxLength={160} />
            {errors.shortDescription && <p className={errorClasses}>{errors.shortDescription.message}</p>}
          </div>

          <div className="sm:col-span-2">
            <label htmlFor="description" className={labelClasses}>Descripción completa *</label>
            <textarea
              id="description"
              {...register('description')}
              rows={5}
              className="w-full rounded-2xl border border-base-300/70 bg-base-100 px-4 py-3 text-sm text-base-content placeholder:text-base-content/40 transition focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/35"
              placeholder="Describí tus servicios, experiencia y enfoque…"
            />
            {errors.description && <p className={errorClasses}>{errors.description.message}</p>}
          </div>

          <div className="sm:col-span-2">
            <label htmlFor="photoUrl" className={labelClasses}>URL de foto</label>
            <input id="photoUrl" {...register('photoUrl')} className={fieldClasses} placeholder="https://..." />
            {errors.photoUrl && <p className={errorClasses}>{errors.photoUrl.message}</p>}
          </div>
        </div>
      </section>

      {/* Contact */}
      <section className="rounded-[2rem] border border-base-300/70 bg-base-200/50 p-6 shadow-sm sm:p-8">
        <h2 className="text-lg font-bold text-base-content">Contacto</h2>
        <p className="mt-1 text-xs text-base-content/60">
          Ingresá al menos un medio de contacto.
        </p>
        <div className="mt-5 grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="phone" className={labelClasses}>Teléfono</label>
            <input id="phone" {...register('phone')} className={fieldClasses} placeholder="099 123 456" />
            {errors.phone && <p className={errorClasses}>{errors.phone.message}</p>}
          </div>
          <div>
            <label htmlFor="whatsapp" className={labelClasses}>WhatsApp</label>
            <input id="whatsapp" {...register('whatsapp')} className={fieldClasses} placeholder="59899123456" />
          </div>
          <div>
            <label htmlFor="email" className={labelClasses}>Email</label>
            <input id="email" type="email" {...register('email')} className={fieldClasses} placeholder="tu@email.com" />
            {errors.email && <p className={errorClasses}>{errors.email.message}</p>}
          </div>
          <div>
            <label htmlFor="website" className={labelClasses}>Sitio web</label>
            <input id="website" {...register('website')} className={fieldClasses} placeholder="https://..." />
            {errors.website && <p className={errorClasses}>{errors.website.message}</p>}
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="instagram" className={labelClasses}>Instagram</label>
            <input id="instagram" {...register('instagram')} className={fieldClasses} placeholder="https://instagram.com/..." />
            {errors.instagram && <p className={errorClasses}>{errors.instagram.message}</p>}
          </div>
        </div>
      </section>

      {/* Location */}
      <section className="rounded-[2rem] border border-base-300/70 bg-base-200/50 p-6 shadow-sm sm:p-8">
        <h2 className="text-lg font-bold text-base-content">Ubicación</h2>
        <div className="mt-5 grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="department" className={labelClasses}>Departamento *</label>
            <select id="department" {...register('department')} className={fieldClasses}>
              <option value="">Seleccionar departamento</option>
              {departmentList.map((dep) => (
                <option key={dep} value={dep}>{dep}</option>
              ))}
            </select>
            {errors.department && <p className={errorClasses}>{errors.department.message}</p>}
          </div>
          <div>
            <label htmlFor="locality" className={labelClasses}>Localidad *</label>
            <select
              id="locality"
              {...register('locality')}
              disabled={!selectedDepartment}
              className={`${fieldClasses} disabled:cursor-not-allowed disabled:opacity-60`}
            >
              <option value="">
                {selectedDepartment ? 'Seleccionar localidad' : 'Elegí departamento primero'}
              </option>
              {localities.map((loc) => (
                <option key={loc} value={loc}>{loc}</option>
              ))}
            </select>
            {errors.locality && <p className={errorClasses}>{errors.locality.message}</p>}
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="address" className={labelClasses}>Dirección</label>
            <input id="address" {...register('address')} className={fieldClasses} placeholder="Dirección física (opcional)" />
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="serviceArea" className={labelClasses}>Zona de servicio</label>
            <input id="serviceArea" {...register('serviceArea')} className={fieldClasses} placeholder="Separá con comas: Minas, Lavalleja, Online" />
          </div>
        </div>
      </section>

      {/* Professional details */}
      <section className="rounded-[2rem] border border-base-300/70 bg-base-200/50 p-6 shadow-sm sm:p-8">
        <h2 className="text-lg font-bold text-base-content">Detalles profesionales</h2>
        <div className="mt-5 grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="tags" className={labelClasses}>Etiquetas</label>
            <input id="tags" {...register('tags')} className={fieldClasses} placeholder="Separá con comas: Presencial, Online, Adultos" />
          </div>
          <div>
            <label htmlFor="availability" className={labelClasses}>Disponibilidad</label>
            <input id="availability" {...register('availability')} className={fieldClasses} placeholder="Ej: Disponible, Agenda limitada" />
          </div>
          <div>
            <label htmlFor="yearsExperience" className={labelClasses}>Años de experiencia</label>
            <input id="yearsExperience" type="number" min="0" {...register('yearsExperience')} className={fieldClasses} />
          </div>
        </div>
      </section>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          type="submit"
          disabled={isSubmitting}
          className="btn btn-primary rounded-full"
        >
          {isSubmitting ? (
            <span className="loading loading-spinner loading-sm" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          {isEditing ? 'Guardar cambios' : 'Crear perfil'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="btn btn-ghost rounded-full text-base-content/60"
        >
          <X className="h-4 w-4" />
          Cancelar
        </button>
      </div>
    </form>
  );
}

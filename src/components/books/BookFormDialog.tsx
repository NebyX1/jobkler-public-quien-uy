import { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import type { Book, BookFormData } from '../../types';

const bookSchema = z.object({
  title: z.string().min(1, 'El título es obligatorio').max(200),
  author: z.string().min(1, 'El autor es obligatorio').max(150),
  isbn: z.string().max(20).optional().or(z.literal('')),
  genre: z.string().max(100).optional().or(z.literal('')),
  year: z
    .number()
    .int()
    .min(1000)
    .max(new Date().getFullYear() + 1)
    .optional()
    .nullable()
    .catch(null),
  publisher: z.string().max(150).optional().or(z.literal('')),
  total_copies: z
    .number()
    .int()
    .min(1, 'Mínimo 1 ejemplar'),
  available_copies: z
    .number()
    .int()
    .min(0)
    .optional()
    .nullable()
    .catch(null),
  description: z.string().optional().or(z.literal('')),
  location: z.string().max(100).optional().or(z.literal('')),
});

type BookFormValues = z.infer<typeof bookSchema>;

interface BookFormDialogProps {
  open: boolean;
  book?: Book | null;
  onClose: () => void;
  onSubmit: (data: BookFormData) => Promise<void>;
  isLoading?: boolean;
}

export function BookFormDialog({
  open,
  book,
  onClose,
  onSubmit,
  isLoading,
}: BookFormDialogProps) {
  const isEdit = !!book;

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<BookFormValues>({
    resolver: zodResolver(bookSchema),
    defaultValues: {
      title: '',
      author: '',
      isbn: '',
      genre: '',
      year: null,
      publisher: '',
      total_copies: 1,
      available_copies: null,
      description: '',
      location: '',
    },
  });

  useEffect(() => {
    if (open) {
      if (book) {
        reset({
          title: book.title,
          author: book.author,
          isbn: book.isbn ?? '',
          genre: book.genre ?? '',
          year: book.year ?? null,
          publisher: book.publisher ?? '',
          total_copies: book.total_copies,
          available_copies: book.available_copies,
          description: book.description ?? '',
          location: book.location ?? '',
        });
      } else {
        reset({
          title: '',
          author: '',
          isbn: '',
          genre: '',
          year: null,
          publisher: '',
          total_copies: 1,
          available_copies: null,
          description: '',
          location: '',
        });
      }
    }
  }, [open, book, reset]);

  const handleFormSubmit = async (values: BookFormValues) => {
    const payload: BookFormData = {
      title: values.title,
      author: values.author,
      isbn: values.isbn || undefined,
      genre: values.genre || undefined,
      year: values.year ?? undefined,
      publisher: values.publisher || undefined,
      total_copies: values.total_copies,
      available_copies: values.available_copies ?? undefined,
      description: values.description || undefined,
      location: values.location || undefined,
    };
    await onSubmit(payload);
  };

  if (!open) return null;

  return (
    <dialog className="modal modal-open" aria-modal="true">
      <div className="modal-box max-w-2xl rounded-3xl border border-quien-border bg-white shadow-soft">
        <h3 className="flex items-center gap-2 text-lg font-bold text-quien-charcoal">
          📖 {isEdit ? 'Editar libro' : 'Nuevo libro'}
        </h3>

        <form onSubmit={handleSubmit(handleFormSubmit)}>
          <div className="max-h-[70vh] overflow-y-auto py-4 pr-1">
            <div className="grid grid-cols-2 gap-4">
              {/* Título */}
              <div className="col-span-2 flex flex-col gap-1.5">
                <label className="text-sm font-semibold text-quien-charcoal">Título *</label>
                <Controller
                  name="title"
                  control={control}
                  render={({ field }) => (
                    <input
                      {...field}
                      placeholder="Título del libro"
                      className="input rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
                    />
                  )}
                />
                {errors.title?.message && (
                  <span className="text-xs text-quien-coral">{errors.title.message}</span>
                )}
              </div>

              {/* Autor */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-semibold text-quien-charcoal">Autor *</label>
                <Controller
                  name="author"
                  control={control}
                  render={({ field }) => (
                    <input
                      {...field}
                      placeholder="Nombre del autor"
                      className="input rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
                    />
                  )}
                />
                {errors.author?.message && (
                  <span className="text-xs text-quien-coral">{errors.author.message}</span>
                )}
              </div>

              {/* ISBN */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-semibold text-quien-charcoal">ISBN</label>
                <Controller
                  name="isbn"
                  control={control}
                  render={({ field }) => (
                    <input
                      {...field}
                      placeholder="978-..."
                      className="input rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
                    />
                  )}
                />
              </div>

              {/* Género */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-semibold text-quien-charcoal">Género</label>
                <Controller
                  name="genre"
                  control={control}
                  render={({ field }) => (
                    <input
                      {...field}
                      placeholder="Novela, Historia, Ciencias..."
                      className="input rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
                    />
                  )}
                />
              </div>

              {/* Editorial */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-semibold text-quien-charcoal">Editorial</label>
                <Controller
                  name="publisher"
                  control={control}
                  render={({ field }) => (
                    <input
                      {...field}
                      placeholder="Editorial"
                      className="input rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
                    />
                  )}
                />
              </div>

              {/* Año */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-semibold text-quien-charcoal">Año</label>
                <Controller
                  name="year"
                  control={control}
                  render={({ field }) => (
                    <input
                      type="number"
                      placeholder="2024"
                      value={field.value?.toString() ?? ''}
                      onChange={(e) => {
                        const v = e.target.value;
                        field.onChange(v ? parseInt(v, 10) : null);
                      }}
                      className="input rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
                    />
                  )}
                />
              </div>

              {/* Total ejemplares */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-semibold text-quien-charcoal">Total ejemplares *</label>
                <Controller
                  name="total_copies"
                  control={control}
                  render={({ field }) => (
                    <input
                      type="number"
                      min={1}
                      value={field.value.toString()}
                      onChange={(e) => field.onChange(parseInt(e.target.value, 10) || 1)}
                      className="input rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
                    />
                  )}
                />
                {errors.total_copies?.message && (
                  <span className="text-xs text-quien-coral">{errors.total_copies.message}</span>
                )}
              </div>

              {/* Disponibles (solo en edición) */}
              {isEdit && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-semibold text-quien-charcoal">Ejemplares disponibles</label>
                  <Controller
                    name="available_copies"
                    control={control}
                    render={({ field }) => (
                      <input
                        type="number"
                        min={0}
                        value={field.value?.toString() ?? '0'}
                        onChange={(e) => field.onChange(parseInt(e.target.value, 10))}
                        className="input rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
                      />
                    )}
                  />
                </div>
              )}

              {/* Ubicación */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-semibold text-quien-charcoal">Ubicación en estante</label>
                <Controller
                  name="location"
                  control={control}
                  render={({ field }) => (
                    <input
                      {...field}
                      placeholder="Ej: Estante A-3"
                      className="input rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
                    />
                  )}
                />
              </div>

              {/* Descripción */}
              <div className="col-span-2 flex flex-col gap-1.5">
                <label className="text-sm font-semibold text-quien-charcoal">Descripción</label>
                <Controller
                  name="description"
                  control={control}
                  render={({ field }) => (
                    <textarea
                      {...field}
                      rows={3}
                      placeholder="Sinopsis o notas sobre el libro..."
                      className="textarea rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
                    />
                  )}
                />
              </div>
            </div>
          </div>

          <div className="modal-action mt-4">
            <button
              type="button"
              onClick={onClose}
              className="btn btn-sm rounded-full border-quien-border bg-white text-quien-charcoal hover:border-quien-green"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-sm rounded-full border-0 bg-quien-green text-white hover:bg-quien-green-dark disabled:opacity-60"
            >
              {isLoading ? 'Guardando...' : isEdit ? 'Guardar cambios' : 'Crear libro'}
            </button>
          </div>
        </form>
      </div>
      <div className="modal-backdrop" onClick={onClose} />
    </dialog>
  );
}

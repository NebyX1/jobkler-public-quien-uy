import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { booksApi } from '../api/books';
import { queryClient } from '../api/queryClient';
import { useBooksStore } from '../store/booksStore';
import { useAuthStore } from '../store/authStore';
import { BookTable } from '../components/books/BookTable';
import { BookFormDialog } from '../components/books/BookFormDialog';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import type { Book, BookFormData } from '../types';
import axios from 'axios';

const AVAILABILITY_OPTIONS = [
  { value: 'all', label: 'Todos' },
  { value: 'available', label: 'Disponibles' },
  { value: 'unavailable', label: 'No disponibles' },
] as const;

export function CatalogPage() {
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';

  const {
    searchQuery, genreFilter, availabilityFilter, page,
    setSearchQuery, setGenreFilter, setAvailabilityFilter, setPage, resetFilters,
  } = useBooksStore();

  const [formOpen, setFormOpen] = useState(false);
  const [editingBook, setEditingBook] = useState<Book | null>(null);
  const [deletingBook, setDeletingBook] = useState<Book | null>(null);
  const [availabilityBook, setAvailabilityBook] = useState<Book | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['books', { search: searchQuery, genre: genreFilter, availability: availabilityFilter, page }],
    queryFn: () =>
      booksApi.list({
        search: searchQuery || undefined,
        genre: genreFilter || undefined,
        availability: availabilityFilter,
        page,
        per_page: 20,
      }),
  });

  const { data: genresData } = useQuery({
    queryKey: ['books-genres'],
    queryFn: booksApi.genres,
    staleTime: 1000 * 60 * 10,
  });

  const createMutation = useMutation({
    mutationFn: (data: BookFormData) => booksApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['books'] });
      queryClient.invalidateQueries({ queryKey: ['books-genres'] });
      setFormOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<BookFormData> }) =>
      booksApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['books'] });
      setFormOpen(false);
      setEditingBook(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => booksApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['books'] });
      setDeletingBook(null);
    },
  });

  const handleFormSubmit = async (formData: BookFormData) => {
    if (editingBook) {
      await updateMutation.mutateAsync({ id: editingBook.id, data: formData });
    } else {
      await createMutation.mutateAsync(formData);
    }
  };

  const handleEdit = (book: Book) => {
    setEditingBook(book);
    setFormOpen(true);
  };

  const handleNewBook = () => {
    setEditingBook(null);
    setFormOpen(true);
  };

  const handleFormClose = () => {
    setFormOpen(false);
    setEditingBook(null);
  };

  const mutationError =
    createMutation.error || updateMutation.error || deleteMutation.error;
  const mutationErrorMsg = mutationError
    ? axios.isAxiosError(mutationError)
      ? mutationError.response?.data?.error ?? 'Error al procesar la operación'
      : 'Error inesperado'
    : null;

  return (
    <div>
      {/* Header */}
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-0.5">
          <h1 className="text-xl font-bold text-quien-charcoal">
            Catálogo de la Biblioteca
          </h1>
          <span className="text-sm text-quien-charcoal/50">
            {data
              ? `${data.total} libro${data.total !== 1 ? 's' : ''} registrado${data.total !== 1 ? 's' : ''}`
              : 'Cargando...'}
          </span>
        </div>
        {isAdmin && (
          <button
            onClick={handleNewBook}
            className="btn btn-sm rounded-full border-0 bg-quien-green text-white hover:bg-quien-green-dark"
          >
            + Nuevo libro
          </button>
        )}
      </div>

      {/* Mutation error */}
      {mutationErrorMsg && (
        <div className="mb-3 rounded-xl border border-quien-coral/30 bg-quien-coral/10 p-3 text-sm text-quien-coral">
          {mutationErrorMsg}
        </div>
      )}

      {/* Filter controls */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          type="text"
          placeholder="🔍 Buscar por título, autor, ISBN..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="input min-w-[280px] rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
        />

        <select
          value={availabilityFilter}
          onChange={(e) => setAvailabilityFilter(e.target.value as typeof availabilityFilter)}
          className="select min-w-[160px] rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
        >
          {AVAILABILITY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        {genresData && genresData.length > 0 && (
          <select
            value={genreFilter}
            onChange={(e) => setGenreFilter(e.target.value)}
            className="select min-w-[160px] rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
          >
            <option value="">Todos los géneros</option>
            {genresData.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        )}

        {(searchQuery || genreFilter || availabilityFilter !== 'all') && (
          <button
            onClick={resetFilters}
            className="btn btn-ghost btn-sm text-quien-charcoal/60"
          >
            ✕ Limpiar filtros
          </button>
        )}
      </div>

      {/* Table card */}
      <div className="overflow-hidden rounded-3xl border border-quien-border bg-white shadow-card">
        {isLoading ? (
          <LoadingSpinner label="Cargando catálogo..." />
        ) : isError ? (
          <div className="m-4 rounded-xl border border-quien-coral/30 bg-quien-coral/10 p-3 text-sm text-quien-coral">
            {axios.isAxiosError(error)
              ? error.response?.data?.error ?? 'Error al cargar los libros'
              : 'Error inesperado'}
          </div>
        ) : (
          <BookTable
            books={data?.items ?? []}
            onEdit={handleEdit}
            onDelete={setDeletingBook}
            onCheckAvailability={setAvailabilityBook}
          />
        )}

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-quien-border p-3">
            <span className="text-xs text-quien-charcoal/50">
              Página {data.page} de {data.pages}
            </span>
            <div className="flex gap-1">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="btn btn-ghost btn-sm text-quien-charcoal/60 disabled:opacity-40"
              >
                ← Anterior
              </button>
              <button
                disabled={page >= data.pages}
                onClick={() => setPage(page + 1)}
                className="btn btn-ghost btn-sm text-quien-charcoal/60 disabled:opacity-40"
              >
                Siguiente →
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Form dialog */}
      <BookFormDialog
        open={formOpen}
        book={editingBook}
        onClose={handleFormClose}
        onSubmit={handleFormSubmit}
        isLoading={createMutation.isPending || updateMutation.isPending}
      />

      {/* Delete confirm */}
      <ConfirmDialog
        open={!!deletingBook}
        title="Eliminar libro"
        message={`¿Estás seguro de que querés eliminar "${deletingBook?.title}"? Esta acción no se puede deshacer.`}
        confirmLabel="Eliminar"
        onConfirm={() => deletingBook && deleteMutation.mutate(deletingBook.id)}
        onCancel={() => setDeletingBook(null)}
        danger
      />

      {/* Availability dialog */}
      {availabilityBook && (
        <dialog className="modal modal-open" aria-modal="true">
          <div className="modal-box max-w-md rounded-3xl border border-quien-border bg-white shadow-soft">
            <h3 className="text-lg font-bold text-quien-charcoal">
              Disponibilidad del libro
            </h3>
            <div className="mt-4 flex flex-col gap-3">
              <div>
                <p className="font-semibold text-quien-charcoal">{availabilityBook.title}</p>
                <p className="text-sm text-quien-charcoal/50">{availabilityBook.author}</p>
              </div>
              <div className="border-t border-quien-border" />
              <div className="flex justify-between">
                <span className="text-sm text-quien-charcoal/70">Total de ejemplares:</span>
                <span className="font-semibold text-quien-charcoal">{availabilityBook.total_copies}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-quien-charcoal/70">Ejemplares disponibles:</span>
                <span className="font-semibold text-quien-charcoal">{availabilityBook.available_copies}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-quien-charcoal/70">Estado:</span>
                <span
                  className={`badge badge-sm rounded-full border-0 ${
                    availabilityBook.is_available
                      ? 'bg-quien-green/10 text-quien-green'
                      : 'bg-quien-coral/10 text-quien-coral'
                  }`}
                >
                  {availabilityBook.is_available ? 'Disponible' : 'Sin ejemplares'}
                </span>
              </div>
              {availabilityBook.location && (
                <div className="flex justify-between">
                  <span className="text-sm text-quien-charcoal/70">Ubicación:</span>
                  <span className="font-semibold text-quien-charcoal">{availabilityBook.location}</span>
                </div>
              )}
            </div>
            <div className="modal-action">
              <button
                onClick={() => setAvailabilityBook(null)}
                className="btn btn-sm rounded-full border-0 bg-quien-green text-white hover:bg-quien-green-dark"
              >
                Cerrar
              </button>
            </div>
          </div>
          <div className="modal-backdrop" onClick={() => setAvailabilityBook(null)} />
        </dialog>
      )}
    </div>
  );
}

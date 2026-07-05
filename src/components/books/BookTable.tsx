import type { Book } from '../../types';
import { useAuthStore } from '../../store/authStore';

interface BookTableProps {
  books: Book[];
  onEdit: (book: Book) => void;
  onDelete: (book: Book) => void;
  onCheckAvailability: (book: Book) => void;
}

export function BookTable({
  books,
  onEdit,
  onDelete,
  onCheckAvailability,
}: BookTableProps) {
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';

  if (books.length === 0) {
    return (
      <div className="p-12 text-center text-quien-charcoal/50">
        <span className="mb-3 block text-5xl opacity-40">📚</span>
        <p className="font-semibold">No se encontraron libros</p>
        <p className="mt-1 text-sm">
          Intente con otros filtros o agregue un nuevo libro al catálogo
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="table w-full">
        <thead>
          <tr className="text-xs uppercase tracking-wider text-quien-charcoal/50">
            <th>Título / Autor</th>
            <th>ISBN</th>
            <th>Género</th>
            <th>Año</th>
            <th>Ejemplares</th>
            <th>Disponibilidad</th>
            <th>Ubicación</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {books.map((book) => (
            <tr key={book.id} className="hover:bg-quien-cream/50">
              <td>
                <span className="block max-w-[260px] truncate font-semibold text-quien-charcoal">
                  {book.title}
                </span>
                <span className="text-xs text-quien-charcoal/50">{book.author}</span>
              </td>
              <td className="font-mono text-xs">{book.isbn ?? '—'}</td>
              <td className="text-sm">{book.genre ?? '—'}</td>
              <td className="text-sm">{book.year ?? '—'}</td>
              <td className="text-sm tabular-nums">
                {book.available_copies} / {book.total_copies}
              </td>
              <td>
                <span
                  className={`badge badge-sm rounded-full border-0 ${
                    book.is_available
                      ? 'bg-quien-green/10 text-quien-green'
                      : 'bg-quien-coral/10 text-quien-coral'
                  }`}
                >
                  {book.is_available ? '✓ Disponible' : '✕ No disponible'}
                </span>
              </td>
              <td className="text-sm">{book.location ?? '—'}</td>
              <td>
                <div className="flex gap-1">
                  <button
                    onClick={() => onCheckAvailability(book)}
                    className="btn btn-ghost btn-xs text-quien-charcoal/60"
                    title="Consultar disponibilidad"
                    aria-label="Consultar disponibilidad"
                  >
                    👁
                  </button>
                  {isAdmin && (
                    <>
                      <button
                        onClick={() => onEdit(book)}
                        className="btn btn-ghost btn-xs text-quien-charcoal/60"
                        title="Editar"
                        aria-label="Editar"
                      >
                        ✏
                      </button>
                      <button
                        onClick={() => onDelete(book)}
                        className="btn btn-ghost btn-xs text-quien-coral"
                        title="Eliminar"
                        aria-label="Eliminar"
                      >
                        🗑
                      </button>
                    </>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  onConfirm,
  onCancel,
  danger = false,
}: ConfirmDialogProps) {
  if (!open) return null;

  return (
    <dialog className="modal modal-open" aria-modal="true">
      <div className="modal-box rounded-3xl border border-quien-border bg-white shadow-soft">
        <h3 className="flex items-center gap-2 text-lg font-bold text-quien-charcoal">
          {danger && <span className="text-quien-coral">⚠</span>}
          {title}
        </h3>
        <p className="mt-3 text-sm text-quien-charcoal/70">{message}</p>
        <div className="modal-action mt-6">
          <button
            className="btn btn-sm rounded-full border-quien-border bg-white text-quien-charcoal hover:border-quien-green"
            onClick={onCancel}
          >
            {cancelLabel}
          </button>
          <button
            className={`btn btn-sm rounded-full border-0 text-white ${
              danger ? 'bg-quien-coral hover:bg-quien-coral/90' : 'bg-quien-green hover:bg-quien-green-dark'
            }`}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
      <div className="modal-backdrop" onClick={onCancel} />
    </dialog>
  );
}

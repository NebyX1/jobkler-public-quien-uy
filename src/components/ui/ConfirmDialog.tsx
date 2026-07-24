import { AlertTriangle } from 'lucide-react';

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
      <div className="modal-box rounded-3xl border border-base-300 bg-base-100 shadow-soft">
        <h3 className="flex items-center gap-2 text-lg font-bold text-base-content">
          {danger && <AlertTriangle className="h-5 w-5 text-error" />}
          {title}
        </h3>
        <p className="mt-3 text-sm text-base-content/70">{message}</p>
        <div className="modal-action mt-6">
          <button
            className="btn btn-sm rounded-full border-base-300 bg-base-100 text-base-content hover:bg-base-200"
            onClick={onCancel}
          >
            {cancelLabel}
          </button>
          <button
            className={`btn btn-sm rounded-full border-0 text-primary-content ${
              danger ? 'btn-error' : 'btn-primary'
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

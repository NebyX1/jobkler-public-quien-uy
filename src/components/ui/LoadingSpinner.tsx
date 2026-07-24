interface LoadingSpinnerProps {
  label?: string;
}

export function LoadingSpinner({ label = 'Cargando...' }: LoadingSpinnerProps) {
  return (
    <div className="flex min-h-[200px] w-full items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <span className="loading loading-spinner loading-lg text-primary" />
        <span className="text-sm text-base-content/60">{label}</span>
      </div>
    </div>
  );
}

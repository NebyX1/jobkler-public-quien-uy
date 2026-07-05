import { useNavigate } from 'react-router-dom';

export function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-quien-cream p-6 text-center">
      <div className="flex flex-col items-center gap-4">
        <span className="text-6xl">🔍</span>
        <h1 className="text-5xl font-extrabold text-quien-charcoal/30">404</h1>
        <p className="text-xl font-bold text-quien-charcoal">Página no encontrada</p>
        <p className="text-quien-charcoal/60">
          La página que buscás no existe o fue movida.
        </p>
        <button
          onClick={() => navigate('/')}
          className="btn mt-2 rounded-full border-0 bg-quien-green px-6 text-white hover:bg-quien-green-dark"
        >
          Volver al inicio
        </button>
      </div>
    </div>
  );
}

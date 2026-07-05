import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { authApi } from '../api/auth';
import { useAuthStore } from '../store/authStore';
import axios from 'axios';

const verifySchema = z.object({
  code: z
    .string()
    .length(6, 'El código debe tener exactamente 6 dígitos')
    .regex(/^\d+$/, 'Solo números'),
});

type VerifyFormValues = z.infer<typeof verifySchema>;

export function Verify2FAPage() {
  const navigate = useNavigate();
  const { pendingToken, setToken, token } = useAuthStore();

  useEffect(() => {
    if (token) { navigate('/dashboard', { replace: true }); return; }
    if (!pendingToken) navigate('/auth', { replace: true });
  }, [pendingToken, token, navigate]);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setFocus,
  } = useForm<VerifyFormValues>({ resolver: zodResolver(verifySchema) });

  useEffect(() => { setFocus('code'); }, [setFocus]);

  const mutation = useMutation({
    mutationFn: ({ code }: VerifyFormValues) =>
      authApi.verify2FA(code, pendingToken!),
    onSuccess: (res) => {
      setToken(res.access_token, res.user);
      navigate('/dashboard', { replace: true });
    },
  });

  const errorMsg = mutation.error
    ? axios.isAxiosError(mutation.error)
      ? mutation.error.response?.data?.error ?? 'Código inválido'
      : 'Error inesperado'
    : null;

  return (
    <div className="flex min-h-screen items-center justify-center bg-quien-cream p-6">
      <div className="w-full max-w-sm rounded-3xl border border-quien-border bg-white p-8 shadow-soft">
        <div className="mb-7 flex flex-col items-center gap-3 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-quien-green text-white">
            🔐
          </div>
          <div>
            <h2 className="text-lg font-bold text-quien-charcoal">
              Verificación 2FA
            </h2>
            <p className="mt-1 text-sm text-quien-charcoal/60">
              Ingresá el código de 6 dígitos que enviamos a tu email
            </p>
          </div>
        </div>

        {errorMsg && (
          <div className="mb-4 rounded-xl border border-quien-coral/30 bg-quien-coral/10 p-3 text-sm text-quien-coral">
            {errorMsg}
          </div>
        )}

        <form
          className="flex flex-col gap-4"
          onSubmit={handleSubmit((d) => mutation.mutate(d))}
        >
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-semibold text-quien-charcoal">
              Código de verificación
            </label>
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              placeholder="000000"
              className="input rounded-2xl border-quien-border bg-white text-center text-2xl tracking-widest tabular-nums text-quien-charcoal focus:border-quien-green focus:outline-none"
              {...register('code')}
            />
            {errors.code?.message && (
              <span className="text-xs text-quien-coral">{errors.code.message}</span>
            )}
          </div>

          <button
            type="submit"
            disabled={mutation.isPending}
            className="btn h-11 rounded-2xl border-0 bg-quien-green text-white hover:bg-quien-green-dark disabled:opacity-60"
          >
            {mutation.isPending ? 'Verificando...' : 'Verificar'}
          </button>

          <div className="text-center">
            <button
              type="button"
              onClick={() => navigate('/auth')}
              className="btn btn-ghost btn-sm text-quien-charcoal/60"
            >
              ← Volver al inicio de sesión
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

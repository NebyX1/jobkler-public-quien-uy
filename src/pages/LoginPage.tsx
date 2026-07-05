import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { authApi } from '../api/auth';
import { useAuthStore } from '../store/authStore';
import type { LoginRequest } from '../types';
import { MathCaptcha } from '../components/ui/MathCaptcha';
import axios from 'axios';

const loginSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(1, 'La contraseña es requerida'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export function LoginPage() {
  const navigate = useNavigate();
  const { setPendingToken, token } = useAuthStore();
  const [captchaValid, setCaptchaValid] = useState(false);
  const [captchaSubmitted, setCaptchaSubmitted] = useState(false);

  useEffect(() => {
    if (token) navigate('/dashboard', { replace: true });
  }, [token, navigate]);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  const mutation = useMutation({
    mutationFn: (data: LoginRequest) => authApi.login(data),
    onSuccess: (res) => {
      setPendingToken(res.pending_token);
      navigate('/verify-2fa');
    },
  });

  const onSubmit = (data: LoginFormValues) => {
    setCaptchaSubmitted(true);
    if (!captchaValid) return;
    mutation.mutate(data);
  };

  const errorMsg = mutation.error
    ? axios.isAxiosError(mutation.error)
      ? mutation.error.response?.data?.error ?? 'Error de conexión'
      : 'Error inesperado'
    : null;

  return (
    <div className="flex min-h-screen items-center justify-center bg-quien-cream p-6">
      <div className="w-full max-w-sm rounded-3xl border border-quien-border bg-white p-8 shadow-soft">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-quien-green text-white">
            📚
          </div>
          <div>
            <h2 className="text-lg font-bold text-quien-charcoal">
              Biblioteca Municipal
            </h2>
            <p className="text-sm text-quien-charcoal/60">
              Casa de la Cultura de Lavalleja
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
          onSubmit={handleSubmit(onSubmit)}
        >
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-semibold text-quien-charcoal">Email</label>
            <input
              type="email"
              placeholder="usuario@ejemplo.com"
              className="input rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
              {...register('email')}
            />
            {errors.email?.message && (
              <span className="text-xs text-quien-coral">{errors.email.message}</span>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-semibold text-quien-charcoal">Contraseña</label>
            <input
              type="password"
              placeholder="••••••••"
              className="input rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
              {...register('password')}
            />
            {errors.password?.message && (
              <span className="text-xs text-quien-coral">{errors.password.message}</span>
            )}
          </div>

          <MathCaptcha
            onValidChange={setCaptchaValid}
            showError={captchaSubmitted}
          />

          <button
            type="submit"
            disabled={mutation.isPending}
            className="btn h-11 rounded-2xl border-0 bg-quien-green text-white hover:bg-quien-green-dark disabled:opacity-60"
          >
            {mutation.isPending ? 'Verificando...' : 'Iniciar sesión'}
          </button>
        </form>
      </div>
    </div>
  );
}

import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(fileURLToPath(new URL('..', import.meta.url)));
const backend = resolve(root, 'backend');
const python = process.platform === 'win32'
  ? resolve(backend, '.venv', 'Scripts', 'python.exe')
  : resolve(backend, '.venv', 'bin', 'python');

if (!existsSync(python)) {
  console.error('No se encontró backend/.venv. Ejecutá run.ps1 o run.sh para preparar el entorno local.');
  process.exit(2);
}

const result = spawnSync(python, ['-m', 'unittest', 'discover', '-s', 'tests', '-v'], {
  cwd: backend,
  stdio: 'inherit',
  env: {
    ...process.env,
    APP_ENV: 'development',
    AUTH_MODE: 'demo',
    ALLOW_DEMO_AUTH: 'true',
    APP_HOST: '127.0.0.1',
    DATABASE_URL: 'sqlite:///jobkler-demo.sqlite3',
    SECRET_KEY: 'isolated-test-only-secret-key-000000000000',
    AUTH_SESSION_SECRET: 'isolated-test-only-session-secret-0000',
    CSRF_SECRET: 'isolated-test-only-csrf-secret-00000000000',
  },
});

if (result.error) {
  console.error(result.error.message);
  process.exit(2);
}
process.exit(result.status ?? 1);

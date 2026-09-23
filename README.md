# Quien.uy local demo

Aplicación React + Vite con API Flask y base SQLite local. El acceso de demostración crea sesiones de backend con cookie HttpOnly; perfiles, reseñas y permisos se guardan y validan en SQLite. No requiere FusionAuth, MariaDB, Redis ni Docker para el uso local.

## Requisitos fijados

- Node.js 22.15.1 (.nvmrc; compatible con Vite 8).
- Python 3.11.0 (.python-version).
- PowerShell 5.1 o Bash.

## Inicio

Windows:

    .\run.ps1
    # Ctrl+C detiene solamente los procesos iniciados por ese script.

Linux:

    bash ./run.sh
    # Ctrl+C detiene solamente los procesos registrados por Jobkler.

Los scripts generan backend/.env y secretos solo cuando hacen falta, instalan dependencias reproducibles, aplican migraciones y ejecutan la semilla idempotente. Revisá logs/ para los registros. La web queda en http://127.0.0.1:5173; Flask escucha en http://127.0.0.1:5000, detrás del proxy /api de Vite.

stop.ps1 y stop.sh paran los PIDs que Jobkler registró y verifican su ruta de ejecución. En Linux, ejecutá `bash ./stop.sh`. Si un puerto está ocupado por otro proceso, el inicio se detiene y muestra el diagnóstico; no mata procesos ajenos. Se pueden cambiar puertos de forma coordinada con:

    .\run.ps1 -ApiPort 5001 -WebPort 5174
    ./run.sh --api-port 5001 --web-port 5174

## Verificación y reset

    npm run verify

Esto compila y revisa el frontend, y ejecuta las pruebas del backend con una base temporal. Requiere haber iniciado una vez para preparar backend/.venv.

El reset es una acción explícita y limitada a la SQLite local de demo:

    Set-Location backend
    .\.venv\Scripts\python.exe -m flask --app wsgi:app reset-demo --yes

    cd backend
    .venv/bin/python -m flask --app wsgi:app reset-demo --yes

El segundo inicio normal conserva perfiles, reseñas, cambios y configuración. La base reside en backend/instance/jobkler-demo.sqlite3. Antes de migrar, el backend exige esa URL exacta en modo demo; si encuentra otra configuración de base, no migra ni siembra.

## Datos de demostración

Los perfiles ficticios incluyen 42 prestadores en Lavalleja, Montevideo, Maldonado y Río Negro. Los valores de perfiles y reseñas son persistentes; los promedios y contadores se calculan desde las reseñas publicadas. Los contactos de la semilla se dejan vacíos y las fotos usan iniciales locales, por lo que no se inicia ninguna comunicación real.

La semilla está versionada y solo agrega registros faltantes una vez. No restaura registros que alguien eliminó después. El reset explícito elimina la base completa de demo y la reconstruye mediante Alembic.

## API y base de datos

- Perfiles públicos y búsqueda: GET /api/profiles.
- Perfil por ID o slug: GET /api/profiles/{id-o-slug}.
- Perfil propio: GET /api/profiles/me.
- Cuenta/sesión: /api/auth/*.
- Categorías y ubicaciones: GET /api/catalog.
- Preparación local: GET /api/health/ready.

Las escrituras con cookie requieren CSRF. La sesión es un token opaco aleatorio cuyo hash se almacena en SQL; logout la revoca. Los IDs y roles recibidos del navegador no otorgan propiedad. Cada cuenta tiene como máximo un perfil; la eliminación de un perfil elimina también sus reseñas. Las cuentas se conservan al borrar un perfil. El rol moderador solo permite ocultar o publicar reseñas.

SQLite es el único motor necesario localmente. La capa SQLAlchemy y los modelos evitan funciones exclusivas de SQLite para facilitar una migración futura a MariaDB. Drivers opcionales de producción están separados en backend/requirements-prod.txt.

## FusionAuth

La demo local es el modo inicial y no cambia automáticamente si FusionAuth falla. Para usar FusionAuth en un entorno local, editá backend/.env manteniendo DATABASE_URL=sqlite:///jobkler-demo.sqlite3, APP_HOST=127.0.0.1, y establecé:

- AUTH_MODE=fusionauth
- FUSIONAUTH_BASE_URL, FUSIONAUTH_ISSUER
- FUSIONAUTH_CLIENT_ID, FUSIONAUTH_CLIENT_SECRET, FUSIONAUTH_GOOGLE_IDP_ID
- FUSIONAUTH_REDIRECT_URI=http://127.0.0.1:5000/api/auth/callback
- AUTH_ALLOWED_REDIRECT_URLS=http://127.0.0.1:5173

El servidor usa Authorization Code + PKCE, state firmado, validación de firma/issuer/audience/subject/expiry y compara el sub de UserInfo con el del ID token. La identidad se vincula por issuer y subject; no por correo. Los roles se asignan localmente. Esta entrega no dispone de credenciales ni una instancia FusionAuth configurada, por lo que el flujo externo no se validó con Google real.

## Búsqueda avanzada futura

La búsqueda actual es pública, léxica y busca en descripciones con normalización de acentos. No interpreta negaciones o intención. Una entrega futura podrá evaluar Qwen3.5-2B GGUF con llama.cpp en CPU únicamente para personas autenticadas. AI_SEARCH_ENABLED=false; no se incluye modelo, RAG, embeddings, Qdrant ni un chatbot simulado.

La verificación descrita es local para Windows con Python 3.11 y Node 22.15.1; no es una validación productiva ni un despliegue.

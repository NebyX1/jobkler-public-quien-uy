# Quien.uy local demo

Aplicación React + Vite con API Flask y base SQLite local. El acceso de demostración crea sesiones de backend con cookie HttpOnly; perfiles, reseñas y permisos se guardan y validan en SQLite. No requiere FusionAuth, MariaDB, Redis ni Docker para el uso local.

## Guías vigentes

- [Instalar desde cero en otro equipo](docs/Guia-para-otro-equipo.md): descargas verificables, arranque, comprobaciones y diagnóstico.
- [Arquitectura actual y diagramas](docs/Arquitectura-Actual.md): componentes, flujo de búsqueda e indexación.
- [Guía del motor Qwen](ai-engine/README.md) y [búsqueda avanzada](docs/Busqueda-Avanzada.md): configuración y comportamiento en detalle.
- [Indicaciones para agentes](AGENTS.md) y [cambios recientes](CHANGELOG.md).

## Requisitos fijados

- Node.js 22.15.1 (.nvmrc; compatible con Vite 8).
- Python 3.11.0 (.python-version).
- PowerShell 5.1 o Bash.
- El modelo GGUF y un servidor llama.cpp compatible en `ai-engine/`. Los modelos y binarios no se incluyen en Git; consultá [la guía del motor](ai-engine/README.md) para prepararlos en cada equipo.

## Inicio

Windows:

    .\run.ps1
    # Ctrl+C detiene solamente los procesos iniciados por ese script.

Linux:

    bash ./run.sh
    # Ctrl+C detiene solamente los procesos registrados por Jobkler.

Los scripts generan la configuración y los secretos cuando hacen falta, instalan dependencias reproducibles, aplican migraciones y ejecutan la semilla idempotente. También preparan e inician el Qwen local autenticado en `127.0.0.1:8081`; la web queda en http://127.0.0.1:5173 y Flask escucha en http://127.0.0.1:5000, detrás del proxy `/api`. Revisá `logs/` para los registros.

`stop.ps1` y `stop.sh` paran los procesos que Jobkler registró, incluido el motor Qwen, y verifican su identidad. En Linux, ejecutá `bash ./stop.sh`. Si un puerto está ocupado por otro proceso, el inicio se detiene y muestra el diagnóstico; no mata procesos ajenos. Se pueden cambiar puertos de forma coordinada con:

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

Los perfiles ficticios incluyen 42 prestadores iniciales, 9 fixtures de búsqueda y 300 perfiles ampliados distribuidos en las diez categorías y los 19 departamentos. De los perfiles ampliados, 210 mencionan trabajos adicionales solo en su descripción, para probar búsquedas de experiencia fuera del oficio principal. Los valores de perfiles y reseñas son persistentes; los promedios y contadores se calculan desde las reseñas publicadas. Los contactos de la semilla se dejan vacíos y las fotos usan iniciales locales, por lo que no se inicia ninguna comunicación real.

Las semillas base y ampliada se aplican una vez y no restauran perfiles que se eliminen después. Los nueve fixtures de búsqueda son distintos: el arranque vuelve a crear los que falten por ID. El reset explícito elimina la base completa de demo y la reconstruye mediante Alembic; los fixtures y la población ampliada se agregan al siguiente arranque normal.

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

La demo local es el modo inicial y no cambia automáticamente si FusionAuth falla. La búsqueda avanzada de esta entrega solo se habilita con autenticación demo local. Para usar FusionAuth en un entorno local, editá backend/.env manteniendo DATABASE_URL=sqlite:///jobkler-demo.sqlite3, APP_HOST=127.0.0.1, desactivá `AI_SEARCH_ENABLED` y establecé:

- AUTH_MODE=fusionauth
- FUSIONAUTH_BASE_URL, FUSIONAUTH_ISSUER
- FUSIONAUTH_CLIENT_ID, FUSIONAUTH_CLIENT_SECRET, FUSIONAUTH_GOOGLE_IDP_ID
- FUSIONAUTH_REDIRECT_URI=http://127.0.0.1:5000/api/auth/callback
- AUTH_ALLOWED_REDIRECT_URLS=http://127.0.0.1:5173

El servidor usa Authorization Code + PKCE, state firmado, validación de firma/issuer/audience/subject/expiry y compara el sub de UserInfo con el del ID token. La identidad se vincula por issuer y subject; no por correo. Los roles se asignan localmente. Esta entrega no dispone de credenciales ni una instancia FusionAuth configurada, por lo que el flujo externo no se validó con Google real.

## Búsqueda avanzada local

La búsqueda común es pública y textual. La búsqueda avanzada requiere sesión y usa Qwen3.5-2B local para interpretar la consulta; combina búsqueda textual en SQLite con un encoder semántico ONNX separado. Si Qwen falla después del arranque, la búsqueda puede continuar en modo reducido y lo indica en la interfaz. Las instrucciones y la configuración del motor están en [ai-engine/README.md](ai-engine/README.md); el funcionamiento de la búsqueda se describe en [docs/Busqueda-Avanzada.md](docs/Busqueda-Avanzada.md).

La verificación descrita es local para Windows con Python 3.11 y Node 22.15.1; no es una validación productiva ni un despliegue.

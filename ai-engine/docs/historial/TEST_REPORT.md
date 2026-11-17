# Test report — Qwen3.5 2B GGUF / llama.cpp

La migración se ejecuta con Qwen3.5-2B Q4_K_M en CPU, llama.cpp y contexto 4096. Se probaron 4, 6, 8 y 12 threads; la configuración recomendada quedó en 4. El benchmark histórico del 0.8B se conserva en `docs/benchmark-qwen35-08b-final.md`; la comparación completa queda en `docs/benchmark-qwen35-08b-vs-2b.md`.

El modelo 2B fue descargado y validado realmente: llama-server cargó la arquitectura y respondió `PONG` por `/v1/chat/completions`. La eliminación física del 0.8B se hará después de completar la batería 2B y guardar la comparación.

## Separación de servicios y despliegue (2026-09-24)

- `backend/.venv/Scripts/python.exe -m pytest backend/tests -q`: 12 pruebas aprobadas. Cubren CRUD y borrado en cascada, historial, UTF-8, CORS, clave Bearer, rechazo de clave incorrecta y acceso administrativo contraseña + TOTP.
- `npm --prefix frontend test`: prueba de botón de borrado aprobada. `npm --prefix frontend run build`: compilación TypeScript/Vite aprobada.
- `npm --prefix llm test` con servidor activo y `RUN_LLM_TESTS=1`: endpoint OpenAI-compatible devuelve 401 sin clave y 200 con clave.
- `docker compose build --parallel`: imágenes frontend, backend y LLM compiladas. `docker compose up -d --build`: las tres llegaron a estado saludable en orden LLM → backend → frontend.
- En contenedores, `/api/chat/stream` produjo `OK`; el mensaje se persistió y la conversación de prueba se borró. El volumen SQLite retuvo una conversación de prueba tras reiniciar backend; luego se eliminó esa conversación.
- `run.ps1` levantó los tres servicios locales en orden y la comprobación final devolvió frontend 200, backend `ready`, LLM `ok`. Los servicios locales permanecen activos para prueba manual.

# Informe de implementación local: Búsqueda Avanzada

Fecha: 2026-09-23  
Proyecto: `jobkler-ai`, rama `feat/jobkler-local-ready`  
Alcance: búsqueda avanzada autenticada con datos ficticios, índice híbrido SQLite/FTS5 + FastEmbed CPU y extracción local con Qwen por llama.cpp.

## Resultado

La función está implementada y activa en la configuración local ignorada por Git. La ruta `/buscar/avanzada` llega a `POST /api/search/advanced`, comprueba sesión y CSRF, valida el contrato, aplica catálogo y cobertura tipada, recupera candidatos por texto y significado, comprueba vigencia y devuelve perfiles con evidencia literal.

La búsqueda pública existente continúa disponible. La interfaz no es conversacional: cada envío es independiente, el usuario inicia la búsqueda manualmente y puede editar ubicación o ampliarla con una acción explícita. La rama SQLite aplica BM25 y la combinación de rankings usa RRF con constante `60`. MariaDB FULLTEXT no se implementó ni se declara validado.

## Validaciones ejecutadas

- `npm run verify`: correcto. TypeScript/Vite, ESLint y 22 pruebas `unittest` pasaron. Vite dejó una advertencia de tamaño del bundle JavaScript (`659.57 kB` sin comprimir, límite de aviso `500 kB`); el build terminó correctamente.
- `python -m compileall -q app tests`: correcto.
- La prueba de sesión anónima devuelve `401` en avanzada; la búsqueda común pública devuelve `200`.
- La API local informa readiness `ready`; el POST avanzado anónimo real devolvió `401`.
- Desde el navegador, la cuenta Cliente Demo envió “¿Hay alguien que arregle termofones en Minas?”. Flask devolvió resultados en estado degradado: seis tarjetas con evidencia literal. La instalación se marcó “Experiencia relacionada”; cobertura local/departamental se rotuló como declarada. No aparecieron el perfil inactivo, la coincidencia de otra localidad sin cobertura ni perfiles con negación explícita. Esta sesión usó el extractor determinista porque Qwen no estaba disponible.
- Una prueba específica confirmó que la rama semántica encuentra un candidato cuando FTS no devuelve candidatos textuales. Esa prueba usa un encoder simulado para aislar la independencia de las ramas.
- FastEmbed descargó y verificó la revisión fijada `faf4aa4225822f3bc6376869cb1164e8e3feedd0`. SHA-256 de `model_optimized.onnx`: `634d0f66c29dc934c8fa72b8a4fe91dd4d420a22f1d82a241058d4316e659a99`. En ejecución produjo un vector CPU de 384 dimensiones, valores finitos y norma `1.0`. La fragmentación real generó 10 fragmentos para una biografía larga, con máximo observado de 111 tokens y la frase final conservada.
- La migración `ad81c0a8e56a` se aplicó a la SQLite demo local. Se insertaron nueve perfiles ficticios, se sincronizaron 51 documentos y el worker produjo 240 fragmentos vigentes en 46 trabajos completados.
- El proceso local quedó iniciado en `http://127.0.0.1:5173`; el indexador persistente está activo. No se detuvo ni modificó el proceso externo llama.cpp.

## Qwen y evaluación pendientes

La URL configurada es `http://127.0.0.1:8081/v1`; `/v1/models` agotó el tiempo de conexión. Por eso no se verificó el alias contra el servidor real ni se hizo una generación real con JSON Schema. El navegador confirmó el modo degradado y la búsqueda determinista, pero el tramo browser → Flask → Qwen sigue pendiente hasta que el servidor vuelva a estar accesible.

Se preparó un corpus de 25 consultas etiquetadas: 12 de calibración y 13 de evaluación, separados en `backend/evaluation/advanced-search.json`. El comando `search-evaluate` mide la búsqueda común, texto-only e híbrida con Qwen/encoder reales; calibration barre umbrales sin modificar `.env`. Se intentaron `search-evaluate --set calibration` y `--set evaluation`: ambos abortaron con `ConnectTimeout` al consultar `/v1/models`, antes de enviar consultas y sin crear métricas ficticias. Quedan pendientes ambas corridas, la revisión del umbral sugerido y los resultados de latencia, memoria, Recall@5 y falsos positivos del corpus real.

En particular, no se afirma que una paráfrasis semántica haya sido recuperada con una respuesta real de Qwen; el modelo de embeddings sí fue descargado, inicializado en CPU e indexó los perfiles locales.

## Datos y límites

Los nueve registros añadidos son fixtures sintéticos, marcados en interfaz y sin contactos ni disponibilidad. Las operaciones de seed, migración y rebuild se ejecutaron sobre `sqlite:///jobkler-demo.sqlite3`; no se apuntaron a una base externa. El archivo `backend/.env` local habilita `AI_SEARCH_ENABLED=true`, autenticación demo y loopback; no se versiona. El alias configurado queda sin confirmar hasta que responda `/v1/models`.

Se requiere un único proceso Flask para que el semáforo local limite inferencia como se espera; el worker de embeddings es otro proceso. Los umbrales y reglas de negación son heurísticas calibrables, no certifican capacidades profesionales ni cubren todas las formas lingüísticas posibles.

## Archivos principales

- Backend: `backend/app/api/advanced_search.py`, `backend/app/search/`, `backend/app/models/jobkler.py`, `backend/migrations/versions/ad81c0a8e56a_advanced_search_index.py` y `backend/app/commands.py`.
- Frontend: `src/pages/AdvancedSearchPage.tsx`, `src/services/advancedSearchService.ts`, `src/router/AppRouter.tsx`, `src/components/landing/SearchPanel.tsx` y `Navbar.tsx`.
- Evaluación y operación: `backend/evaluation/advanced-search.json`, `backend/tests/test_advanced_search.py`, `docs/Busqueda-Avanzada.md`, `run.ps1`, `run.sh`, `stop.ps1` y `stop.sh`.

La documentación de arquitectura, contratos, comandos y límites está en [Busqueda-Avanzada.md](Busqueda-Avanzada.md). Referencias de llama.cpp, FastEmbed, FTS5 y RRF se encuentran allí.

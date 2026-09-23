# Búsqueda Avanzada local

## Recorrido

La ruta React `/buscar/avanzada` envía cada consulta manual a `POST /api/search/advanced`. Flask exige sesión de Jobkler y CSRF antes de usar Qwen. Una consulta JSON pequeña se interpreta con una sola llamada a la API local de llama.cpp; Pydantic vuelve a validar el contrato. Si Qwen no responde o entrega JSON inválido, se usa el extractor determinista y la respuesta queda marcada como degradada. Saturación o límite de tiempo se informan como estado recuperable, sin reintentar.

La recuperación aplica primero los filtros de profesión, localidad y cobertura declarada a ambas ramas. SQLite FTS5 consulta el documento completo de perfil y ordena con BM25. En paralelo, NumPy puntúa contra los fragmentos vigentes de todos los perfiles geográficamente elegibles; esa rama no depende de que FTS encuentre candidatos. Los rankings se combinan con Reciprocal Rank Fusion, `k=60`. Finalmente, SQL vuelve a comprobar publicación y hash y solo entonces arma tarjetas con evidencia literal del perfil actual.

La búsqueda común sigue siendo pública y mantiene su ruta existente. La avanzada no manda la consulta ni credenciales directamente al navegador hacia llama.cpp.

## Datos e índice

- `profiles` permanece como fuente canónica. Los cambios actualizan el documento FTS en la misma transacción y agregan un trabajo persistente para embeddings.
- `profile_search_documents` conserva campos públicos de profesión, categoría, descripción corta, `description` y tags. No incluye contactos, dirección ni ubicación como sustituto de filtros.
- `profile_search_chunks` guarda texto literal, campo de origen, offsets, hash de fuente, revisión del encoder, dimensión, tipo `float32-le` y bytes del vector. La ficha pública se vuelve a hidratar desde `profiles`.
- `profile_coverages` contiene únicamente valores `serviceArea` que resolvieron sin ambigüedad contra el catálogo. Una mención en la biografía nunca otorga cobertura.
- `profile_search_index_jobs` procesa embeddings fuera de la transacción del perfil. Antes de publicar, el worker comprueba estado activo y revisión/hash; un trabajo obsoleto no reemplaza la nueva revisión.
- FTS5 usa tokenizer Unicode con eliminación de diacríticos. Se implementa y valida el adaptador SQLite activo; no se declara compatibilidad probada con MariaDB.

El encoder CPU es `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, artefacto ONNX de Qdrant, revisión `faf4aa4225822f3bc6376869cb1164e8e3feedd0`, FastEmbed `0.6.1`, 384 dimensiones y hasta 128 tokens. El manifiesto de descarga registra SHA-256. El cache vive bajo `backend/instance/fastembed/` y Git lo ignora. El procesamiento reserva tokens especiales, genera ventanas solapadas y conserva posiciones literales, incluso al final de biografías largas.

Qwen se configura con `AI_LLM_BASE_URL` y el alias real visible en `/v1/models`. La llamada usa JSON Schema, `stream=false`, hasta 256 tokens y pensamiento desactivado. El límite total inicial es 20 s y la conexión se limita a 2 s. Un semáforo protege una única instancia del servidor Flask; esta primera versión debe ejecutarse como un proceso Flask, además del worker de embeddings.

## Interfaz y evidencia

El formulario envía al pulsar Buscar o Enter y acepta filtros de departamento/localidad. Una contradicción o escritura dudosa pide selección; no escoge una ubicación automáticamente. Sin ubicación se busca a nivel nacional. La UI diferencia coincidencia directa y relacionada, y muestra el texto literal que fundamenta cada perfil. Si no hay resultados, ampliar el área es una acción explícita. No se afirma disponibilidad ni se convierten instalaciones en reparaciones. Los perfiles ficticios llevan marca visible de fixture y la tarjeta ya no inventa una reseña de cero.

Las reglas de negación cubren patrones frecuentes y comprobados, como “no reparo” y “no declaro trabajos de reparación”. No son comprensión exhaustiva de toda redacción. Evidencia semántica sin declaración directa se presenta como relacionada.

## Preparación local

En `backend/.env`, usar solo la base demo local indicada y mantener `APP_ENV=development`, `AUTH_MODE=demo`, `ALLOW_DEMO_AUTH=true`, `APP_HOST=127.0.0.1` y `AI_SEARCH_ENABLED=true`. Los secretos locales los crea el script de preparación; el archivo `.env` no se versiona.

Windows:

```powershell
.\run.ps1
```

Linux:

```bash
./run.sh
```

Los scripts revisan puertos sin terminar procesos ajenos, migran solo `sqlite:///jobkler-demo.sqlite3`, agregan fixtures una sola vez, reconstruyen FTS, preparan el encoder, consultan `/v1/models` sin iniciar ni modificar llama.cpp, inician Flask y Vite, y mantienen un worker persistente si el encoder está listo.

Comandos útiles desde `backend/`:

```bash
python -m flask --app wsgi:app search-model-check
python -m flask --app wsgi:app search-model-prepare
python -m flask --app wsgi:app seed-search-fixtures
python -m flask --app wsgi:app search-rebuild
python -m flask --app wsgi:app search-index-status
python -m flask --app wsgi:app search-worker
python -m flask --app wsgi:app search-check-llm
python -m flask --app wsgi:app search-evaluate --set calibration
python -m flask --app wsgi:app search-evaluate --set evaluation
```

`search-evaluate` requiere Qwen y el corpus vectorial completo. Para cada consulta etiquetada hace una sola petición de extracción, compara top 5 híbrido, texto-only y el buscador público, y escribe JSON bajo `backend/instance/evaluation/`. Reporta Recall@5 macro, Hit@5, precisión de cero resultados, perfiles etiquetados como prohibidos, exactitud de estado, latencias por fase, condiciones de caché y memoria del proceso CLI. En `calibration` barre umbrales 0.45–0.70 y recomienda el que maximiza la media armónica entre Recall@5 macro y especificidad sobre perfiles explícitamente prohibidos, con desempates documentados; no modifica `.env`. `evaluation` mide el umbral configurado y no se usa para ajustarlo. `qwen_plus_hybrid` mide Qwen, la vectorización de la consulta y recuperación dentro del servicio; no incluye latencia del navegador ni la capa HTTP de Flask.

Los tests simulados se ejecutan con:

```powershell
backend\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
npm run verify
```

## Límites

La instalación actual valida SQLite/FTS5; no implementa adaptador MariaDB. El cálculo de coseno lee los vectores vigentes de los perfiles elegibles dentro de la petición y no mantiene una caché global. Los filtros obligatorios preceden a ambas recuperaciones. Un umbral de coseno o el ranking no certifica la habilidad de una persona: la UI conserva la declaración de origen y diferencia evidencia relacionada. Las medidas de rendimiento son válidas solo para el equipo y las condiciones guardadas junto a cada evaluación.

## Referencias técnicas

- [Documentación del servidor HTTP de llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) y [gramáticas/JSON Schema](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md).
- [Artefacto ONNX de Qdrant para FastEmbed](https://huggingface.co/Qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q) y [ficha original multilingüe](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2).
- [SQLite FTS5](https://www.sqlite.org/fts5.html) para tokenizer Unicode, consultas parametrizadas y BM25.
- [Reciprocal Rank Fusion](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking) para combinar listas con escalas distintas.

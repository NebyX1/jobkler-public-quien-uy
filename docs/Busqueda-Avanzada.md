# Búsqueda Avanzada local

## Recorrido

El chat en `/buscar/avanzada` envía cada mensaje a `POST /api/search/advanced`. Flask exige sesión de Jobkler y CSRF antes de usar Qwen. Cada consulta se interpreta con una llamada a la API local de llama.cpp y Pydantic valida la respuesta. Si Qwen no responde o entrega JSON inválido, se usa el extractor determinista y la respuesta indica que la búsqueda funcionó en modo reducido.

El chat solicita `Accept: application/x-ndjson` para recibir las etapas `interpretation`, `location` y `retrieval` a medida que empieza cada una. Un evento final `result` trae la respuesta y el código de estado de la búsqueda. Los clientes que solicitan JSON reciben la respuesta completa al finalizar. Los errores de sesión y validación conservan su código HTTP y formato JSON.

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

Qwen se configura con `AI_LLM_BASE_URL` y el alias real visible en `/v1/models`. Si el servidor exige autenticación, configurá también `AI_LLM_API_KEY` en `backend/.env` con la misma clave que usa el servidor; el backend la envía como Bearer y nunca al navegador. La llamada usa JSON Schema, `stream=false`, hasta 256 tokens y pensamiento desactivado. El límite inicial de inferencia es 20 s y la conexión se limita a 2 s. Si otra consulta está usando el modelo, se espera hasta 10 s por defecto antes de informar que está ocupado; ese tiempo se puede ajustar con `AI_SEARCH_QUEUE_WAIT_SECONDS`. Un semáforo protege una única instancia del servidor Flask; esta primera versión debe ejecutarse como un proceso Flask, además del worker de embeddings.

## Interfaz y evidencia

La ventana inicial ofrece un campo de mensaje y ejemplos. Al enviar, el asistente aplica automáticamente la localidad o el departamento reconocido en el catálogo y muestra la zona en la respuesta, incluso si la búsqueda queda vacía. Si el nombre es dudoso o hay varias ubicaciones posibles, ofrece opciones para confirmar. Cada nuevo mensaje inicia una búsqueda independiente. El historial visible vive en la página y se borra al abrir un nuevo chat o recargar.

Si el usuario omite la ubicación, se busca en todo Uruguay. El botón **Buscar en todo Uruguay** vuelve a buscar el mismo servicio con `locationScope: "national"`. El contrato admite `departmentId` y `localityId` al elegir una ubicación sugerida. La interfaz diferencia coincidencias directas y relacionadas, conserva el fragmento del perfil publicado e indica cuándo el perfil es ficticio.

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

Los scripts revisan puertos sin terminar procesos ajenos, migran solo `sqlite:///jobkler-demo.sqlite3`, agregan los fixtures de búsqueda faltantes por ID, reconstruyen FTS y preparan el encoder. Con la configuración predeterminada también inician el servidor de `ai-engine/`, verifican su modelo y arrancan Flask, Vite y el worker de embeddings. La guía de archivos, claves y uso del motor está en [ai-engine/README.md](../ai-engine/README.md).

La semilla ampliada agrega 300 perfiles ficticios en las diez categorías y los 19 departamentos; 210 declaran trabajos adicionales únicamente en la descripción. Por ejemplo, se pueden buscar instalación de aire acondicionado, reparación de termofones, fotografía de productos o cuidado de mascotas, aun cuando el perfil tenga otra actividad principal. Se aplica una sola vez y no restaura perfiles editados o borrados.

Comandos útiles desde `backend/`:

```bash
python -m flask --app wsgi:app search-model-check
python -m flask --app wsgi:app search-model-prepare
python -m flask --app wsgi:app seed-search-fixtures
python -m flask --app wsgi:app seed-expanded-profiles
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

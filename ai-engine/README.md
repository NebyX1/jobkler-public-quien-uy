# Motor local Qwen para Jobkler

Esta carpeta reúne el servidor de inferencia `llama.cpp`, el modelo Qwen3.5-2B y las herramientas para usarlos con la búsqueda avanzada de Jobkler. La aplicación no necesita la carpeta `chat-onnx-local`: Flask envía la consulta al servidor local, Qwen interpreta el pedido y el buscador combina texto y embeddings para recuperar perfiles.

```text
Navegador → Vite :5173 → Flask :5000 → Qwen/llama.cpp :8081
                              └──────→ SQLite + encoder semántico ONNX
```

## Archivos

```text
ai-engine/
├── engine.py             # configuración, arranque, estado y detención del servidor
├── run.ps1 / stop.ps1    # motor por separado en Windows
├── run.sh / stop.sh      # motor por separado en Linux
├── .env.example          # configuración de ejemplo sin secretos
├── bin/                  # llama-server y sus bibliotecas para la plataforma
├── models/               # Qwen3.5-2B-Q4_K_M.gguf
├── scripts/              # herramientas de medición
├── test/                 # pruebas de configuración y contrato HTTP
├── docs/historial/       # informes de la instalación de origen
└── Dockerfile            # alternativa independiente para el servidor LLM
```

La copia local de Windows usa CPU, cuatro hilos, contexto 4096 y llama.cpp `build 11052`, commit `eb1e1f495`. El modelo pesa aproximadamente 1,27 GB; el SHA-256 de la copia verificada es `0bfe35afc9f05b7fac3fa04925e051ac7939a42a8a17ea11afc99701bea826cc`. La GPU no se usa con la configuración predeterminada.

En `docs/historial/` se conservan las mediciones y el informe originales de `chat-onnx-local`. Son antecedentes de esa aplicación y de ese momento; las instrucciones vigentes para Jobkler son las de esta guía.

## Iniciar todo el proyecto

Desde la raíz de Jobkler, en Windows:

```powershell
.\run.ps1
```

Para dejar los servicios corriendo al volver a la consola, usá `.\run.ps1 -NoWait`. Abrí [http://127.0.0.1:5173/buscar/avanzada](http://127.0.0.1:5173/buscar/avanzada), elegí una cuenta de demostración y realizá la búsqueda. El primer inicio puede tardar por la instalación de dependencias y la preparación del encoder semántico.

Para detener los procesos registrados de Jobkler, incluido Qwen:

```powershell
.\stop.ps1
```

En Linux los comandos equivalentes son `bash ./run.sh` y `bash ./stop.sh`. Antes hay que colocar un `llama-server` nativo de Linux y sus bibliotecas en `ai-engine/bin/`; los ejecutables `.exe` copiados son de Windows y no funcionan en Linux. El arranque integrado se probó en Windows; la ruta Linux no se ejecutó en este equipo.

## Usar o inspeccionar solo el motor

Después de preparar al menos una vez `backend/.env` mediante el arranque principal:

```powershell
.\ai-engine\run.ps1
python .\ai-engine\engine.py status
.\ai-engine\stop.ps1
```

En Linux se pueden usar `bash ai-engine/run.sh`, `python3.11 ai-engine/engine.py status` y `bash ai-engine/stop.sh`. `status` informa si el proceso registrado está activo y si el modelo responde. Los logs están en `logs/ai-engine.log` y `logs/ai-engine-error.log`; el PID y la identidad del proceso quedan en `.jobkler/ai-engine.pid`.

El motor solo escucha en `127.0.0.1:8081`. Su endpoint `/v1/models` y las solicitudes de inferencia requieren una clave Bearer. El controlador comprueba el ejecutable y la fecha de creación del proceso antes de detenerlo. Si el puerto está ocupado por un proceso que Jobkler no administra, el inicio se detiene y muestra el conflicto sin terminar ese proceso.

## Configuración

El primer arranque crea `backend/.env` y `ai-engine/.env` a partir de sus ejemplos cuando faltan. Si no existe una clave compartida, genera una aleatoria y la guarda en ambos archivos. Si ya existen claves distintas, detiene el inicio y pide corregirlas; no reemplaza ninguna automáticamente. Los `.env` están excluidos de Git y la clave no se envía al navegador.

Valores locales principales:

| Archivo | Variable | Valor inicial |
| --- | --- | --- |
| `backend/.env` | `AI_LLM_MANAGED` | `true` |
| `backend/.env` | `AI_LLM_BASE_URL` | `http://127.0.0.1:8081/v1` |
| `backend/.env` | `AI_LLM_MODEL` | `Qwen3.5-2B-Q4_K_M.gguf` |
| `backend/.env` | `AI_LLM_API_KEY` | La misma clave que `LLM_API_KEY` |
| `ai-engine/.env` | `LLM_HOST`, `LLM_PORT` | `127.0.0.1`, `8081` |
| `ai-engine/.env` | `LLM_MODEL` | `models/Qwen3.5-2B-Q4_K_M.gguf` |
| `ai-engine/.env` | `LLM_MODEL_ALIAS` | `Qwen3.5-2B-Q4_K_M.gguf` |
| `ai-engine/.env` | `LLM_CONTEXT`, `LLM_THREADS`, `LLM_GPU_LAYERS` | `4096`, `4`, `0` |

El puerto y el alias deben coincidir en ambos archivos. Para cambiar la clave, detené el motor, dejá vacíos **ambos** campos de clave y ejecutá el arranque principal para generar otra. Si se prefiere un servidor ya administrado por fuera de Jobkler, configurá `AI_LLM_MANAGED=false` en `backend/.env` y ajustá la URL, el alias y la clave de ese servidor; Jobkler no lo iniciará ni lo detendrá.

## Copiar o reconstruir en otra computadora

El GGUF y los binarios se excluyen de Git por su tamaño. La [guía de instalación desde cero](../docs/Guia-para-otro-equipo.md) incluye comandos completos para descargarlos y verificar sus hashes. Al copiar esta carpeta manualmente, incluí `bin/` y `models/`; al clonar el repositorio, preparalos por separado:

1. Descargá [Qwen3.5-2B-Q4_K_M.gguf, revisión fijada](https://huggingface.co/lmstudio-community/Qwen3.5-2B-GGUF/blob/bb84e11355a036e28f080c7793fa6d22b7c4e344/Qwen3.5-2B-Q4_K_M.gguf) y guardalo en `ai-engine/models/` con ese nombre. Verificá el SHA-256 anterior para obtener la misma copia usada aquí. El archivo de igual nombre del repositorio de Unsloth tiene otro hash y no es esta copia exacta.
2. Para Windows x64 CPU, obtené el paquete de [llama.cpp build 11052](https://github.com/ggml-org/llama.cpp/releases/tag/b11052) y colocá `llama-server.exe` **con todas sus DLL** en `ai-engine/bin/`. En Linux usá el binario nativo compatible y sus bibliotecas.
3. Instalá Python 3.11 y Node 22.15.1 y ejecutá el arranque principal. No copies `.env` con secretos si no deseás compartirlos: el primer inicio puede generarlos de nuevo.

El `Dockerfile` de esta carpeta es una alternativa para el servidor LLM, no forma parte del arranque nativo de Jobkler. Si se ejecuta por separado, montá el GGUF, configurá la misma clave y seleccioná `AI_LLM_MANAGED=false` en el backend. La integración Docker no se verificó en esta modificación.

## Comprobaciones y problemas habituales

- `python ai-engine/engine.py status` debe indicar `running: true` y `ready: true`.
- Si falta el modelo o el ejecutable, revisá las rutas anteriores. Si el puerto 8081 está ocupado, detené el servicio que lo ocupa o configurá un puerto libre de forma coordinada en ambos `.env`.
- Si las claves no coinciden o el alias es distinto, revisá la configuración de ambos archivos sin publicar los valores secretos.
- Qwen procesa una consulta por vez. Una solicitud adicional espera hasta 10 segundos por defecto; si sigue ocupado, la interfaz pide reintentar. El límite de espera se ajusta con `AI_SEARCH_QUEUE_WAIT_SECONDS` en `backend/.env`.
- `npm --prefix ai-engine test` ejecuta las pruebas locales de configuración. El contrato HTTP real requiere el servidor activo y `RUN_LLM_TESTS=1` junto con `LLM_API_KEY` en el entorno del proceso.

El modelo GGUF y el proyecto llama.cpp tienen sus propias licencias: consultá la [ficha del modelo](https://huggingface.co/lmstudio-community/Qwen3.5-2B-GGUF) y el [repositorio de llama.cpp](https://github.com/ggml-org/llama.cpp). La licencia de LLVM OpenMP incluida con los binarios está en `bin/LICENSE-LLVM-OpenMP`.

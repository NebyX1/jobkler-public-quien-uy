# Guía para iniciar Jobkler en otro equipo

Esta guía permite a una persona o a un agente preparar una instalación local desde un clon limpio. Los comandos se ejecutan desde la raíz del repositorio, salvo que se indique otra carpeta.

## 1. Requisitos y archivos externos

- [Git](https://git-scm.com/downloads), [Node.js 22.15.1](https://nodejs.org/en/download/archive/v22.15.1) con npm y [Python 3.11](https://www.python.org/downloads/release/python-3110/). El proyecto acepta Node 22.12 o posterior de la rama 22 y Python 3.11.x; las versiones de referencia probadas son Node 22.15.1 y Python 3.11.0. En Windows, PowerShell 5.1 o superior; en Linux, Bash.
- Conexión a Internet durante la preparación: se descargan dependencias, el GGUF, el ejecutable de llama.cpp y el encoder ONNX fijado. El primer inicio puede tardar varios minutos.
- Espacio para el modelo GGUF de 1,27 GB, el encoder de aproximadamente 267 MB y las dependencias. La memoria y el tiempo de inferencia dependen del equipo; el modo predeterminado usa CPU.
- Puertos locales libres: **5173** para Vite, **5000** para Flask y **8081** para Qwen.

El repositorio **no incluye** los pesos, los ejecutables de llama.cpp, `.env`, `node_modules`, el entorno virtual, la SQLite ni los logs. No hay que copiar secretos de otra máquina: el primer inicio crea claves locales nuevas cuando faltan.

```text
git clone https://github.com/NebyX1/jobkler-public-quien-uy.git
cd jobkler-public-quien-uy
```

### Archivos que deben existir antes de iniciar

| Archivo | Propósito | SHA-256 |
| --- | --- | --- |
| `ai-engine/models/Qwen3.5-2B-Q4_K_M.gguf` | Interpretación local con Qwen | `0bfe35afc9f05b7fac3fa04925e051ac7939a42a8a17ea11afc99701bea826cc` |
| `ai-engine/bin/llama-server.exe` y sus DLL | Servidor CPU para Windows x64 | Paquete `b11052` abajo |
| `ai-engine/bin/llama-server` y sus bibliotecas | Servidor nativo para Linux x64 | Paquete `b11052` abajo |

El encoder [Qdrant MiniLM ONNX](https://huggingface.co/Qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q/tree/faf4aa4225822f3bc6376869cb1164e8e3feedd0) se descarga durante el arranque, en la revisión fijada `faf4aa4225822f3bc6376869cb1164e8e3feedd0`. Es independiente de Qwen y queda en `backend/instance/fastembed/`.

## 2. Preparación en Windows x64

Verificá las versiones:

```powershell
node --version
py -3.11 --version
```

Si no está instalado el lanzador `py`, verificá `python --version`; `run.ps1` también acepta `python` cuando es Python 3.11.

Desde la raíz, descargá el paquete CPU oficial de llama.cpp, comprobá su hash y extraé **todos** sus archivos en `ai-engine/bin/`. El ZIP de esta versión contiene el ejecutable y las DLL en su raíz:

```powershell
New-Item -ItemType Directory -Force -Path .\ai-engine\bin, .\ai-engine\models | Out-Null
$runtimeZip = Join-Path $env:TEMP 'jobkler-llama-b11052-win-cpu-x64.zip'
curl.exe -fL --retry 3 -o $runtimeZip 'https://github.com/ggml-org/llama.cpp/releases/download/b11052/llama-b11052-bin-win-cpu-x64.zip'
if ($LASTEXITCODE -ne 0) { throw 'Falló la descarga de llama.cpp.' }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $runtimeZip).Hash -ne '073e460d5e9525ea3773591daca1cd6d9731b504a4a33e5136a13ccb88ee6478') { throw 'El SHA-256 de llama.cpp no coincide.' }
Expand-Archive -LiteralPath $runtimeZip -DestinationPath .\ai-engine\bin -Force
```

Descargá la revisión exacta del modelo y verificá su hash:

```powershell
$modelPath = '.\ai-engine\models\Qwen3.5-2B-Q4_K_M.gguf'
curl.exe -fL --retry 3 -o $modelPath 'https://huggingface.co/lmstudio-community/Qwen3.5-2B-GGUF/resolve/bb84e11355a036e28f080c7793fa6d22b7c4e344/Qwen3.5-2B-Q4_K_M.gguf'
if ($LASTEXITCODE -ne 0) { throw 'Falló la descarga del modelo GGUF.' }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $modelPath).Hash -ne '0bfe35afc9f05b7fac3fa04925e051ac7939a42a8a17ea11afc99701bea826cc') { throw 'El SHA-256 del modelo no coincide.' }
```

También podés copiar `ai-engine/bin/` y `ai-engine/models/` desde una instalación de Windows x64 ya preparada y verificar el hash del GGUF. No copies `backend/.env` ni `ai-engine/.env` si querés generar claves independientes.

Iniciá todo el proyecto:

```powershell
.\run.ps1 -NoWait
```

El script crea las configuraciones locales que falten, prepara dependencias, migra y siembra SQLite, prepara los índices y arranca Qwen, Flask, el indexador y Vite. `-NoWait` devuelve el control a la consola; sin ese parámetro, `Ctrl+C` finaliza los procesos iniciados por el script. Para detener los servicios registrados:

```powershell
.\stop.ps1
```

## 3. Preparación en Linux x64

La ruta Linux está implementada, pero **no se probó de extremo a extremo en esta entrega**. El siguiente paquete es para Ubuntu x64 CPU; en otra arquitectura elegí un binario nativo compatible. Los ejecutables de Windows no funcionan en Linux.

```bash
(
set -euo pipefail
node --version
python3.11 --version
mkdir -p ai-engine/bin ai-engine/models
runtime_tar="${TMPDIR:-/tmp}/jobkler-llama-b11052-ubuntu-x64.tar.gz"
curl -fL --retry 3 -o "$runtime_tar" 'https://github.com/ggml-org/llama.cpp/releases/download/b11052/llama-b11052-bin-ubuntu-x64.tar.gz'
printf '%s  %s\n' '4393f4e075757857d1f361420487d9d602516c64f7cd8c0035e1758e0c72355a' "$runtime_tar" | sha256sum -c -
tar -xzf "$runtime_tar" -C ai-engine/bin --strip-components=1
chmod u+x ai-engine/bin/llama-server
model_path='ai-engine/models/Qwen3.5-2B-Q4_K_M.gguf'
curl -fL --retry 3 -o "$model_path" 'https://huggingface.co/lmstudio-community/Qwen3.5-2B-GGUF/resolve/bb84e11355a036e28f080c7793fa6d22b7c4e344/Qwen3.5-2B-Q4_K_M.gguf'
printf '%s  %s\n' '0bfe35afc9f05b7fac3fa04925e051ac7939a42a8a17ea11afc99701bea826cc' "$model_path" | sha256sum -c -
bash ./run.sh --no-wait
)
```

Para detener los servicios registrados: `bash ./stop.sh`.

## 4. Comprobar que funciona

1. Abrí [http://127.0.0.1:5173](http://127.0.0.1:5173), ingresá con **Cliente Demo** y abrí **Búsqueda Avanzada**.
2. Buscá `Hay alguien que coloque aires acondicionados?`. En una base recién sembrada deben aparecer perfiles ficticios con evidencia en sus descripciones. Los resultados pueden variar si se editó la base o cambia el modelo.
3. Revisá el motor desde la raíz: `python ai-engine/engine.py status` en Windows o `python3.11 ai-engine/engine.py status` en Linux. Debe indicar `running: true` y `ready: true`.
4. Consultá `http://127.0.0.1:5173/api/health/ready`: debe responder con `status: ready` y `database: ok`. Esta comprobación verifica Flask y SQLite; **no** confirma por sí sola que Qwen o el índice semántico estén listos.
5. Ejecutá `npm run verify` desde la raíz para compilar el frontend, pasar ESLint y correr las pruebas del backend. El comando requiere que el inicio haya creado `backend/.venv`. Las pruebas automatizadas no equivalen por sí solas a una búsqueda real con Qwen.

Para revisar la cola de embeddings y la conexión al modelo en Windows:

```powershell
Push-Location .\backend
.\.venv\Scripts\python.exe -m flask --app wsgi:app search-index-status
.\.venv\Scripts\python.exe -m flask --app wsgi:app search-check-llm
Pop-Location
```

En Linux, desde `backend/`, usá `.venv/bin/python -m flask --app wsgi:app` con los mismos subcomandos. El indexador funciona en segundo plano: al principio puede haber trabajos `pending` o `running`; esperá a que terminen antes de evaluar recuperación semántica.

## 5. Diagnóstico rápido

| Síntoma | Comprobación y acción |
| --- | --- |
| PowerShell bloquea la ejecución de scripts | En esa consola podés iniciar con `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 -NoWait`; el ajuste se limita a ese proceso. |
| Falta `llama-server` o el GGUF | Revisá las rutas de la sección 1 y las descargas de la plataforma correcta. No alcanza con copiar el `.exe` sin sus DLL. |
| Puerto 5000, 5173 u 8081 ocupado | Identificá el servicio que lo usa. Los scripts no terminan procesos ajenos. Para API y web pueden usarse `-ApiPort 5001 -WebPort 5174` o `--api-port 5001 --web-port 5174`; para Qwen, coordiná `LLM_PORT` y `AI_LLM_BASE_URL` en ambos `.env`. |
| Las claves o el alias no coinciden | Compará `AI_LLM_API_KEY` con `LLM_API_KEY` y `AI_LLM_MODEL` con `LLM_MODEL_ALIAS` sin imprimir ni compartir secretos. Las claves existentes no se reemplazan automáticamente. |
| Qwen no responde o la búsqueda aparece reducida | Revisá `python ai-engine/engine.py status`, `logs/ai-engine-error.log` y `logs/api-error.log`. Una respuesta 401 de `/v1/models` **sin** clave es esperada. |
| Motor ocupado o HTTP 503 | Qwen atiende una inferencia a la vez. La siguiente solicitud espera hasta 10 segundos por defecto; si se agota el plazo, volvé a intentar. |
| El encoder o los vectores faltan | Revisá `logs/indexer-error.log`, conexión a Hugging Face y `search-index-status`. Si el encoder no se prepara, la búsqueda puede funcionar con recuperación textual reducida. |
| `npm run verify` no encuentra Python | Ejecutá primero el arranque para crear `backend/.venv`; confirmá que Python 3.11 esté disponible. |

Más detalles de procesos y configuración: [guía del motor](../ai-engine/README.md). Los archivos de log están en `logs/`; la configuración sensible está en `backend/.env` y `ai-engine/.env` y no debe compartirse ni subirse a Git.

## 6. Llevar datos de una instalación existente

Un clon limpio crea una SQLite nueva con datos de demostración; no trae los perfiles editados ni las reseñas creadas en otra computadora. Para conservarlos, detené Jobkler en el equipo de origen, comprobá que ninguna otra aplicación esté escribiendo la base y copiá `backend/instance/jobkler-demo.sqlite3` a la misma ruta del equipo de destino. Si en el destino ya hay una base que querés conservar, guardá una copia antes de reemplazarla. Después iniciá Jobkler normalmente: el arranque aplica las migraciones y sincroniza los índices.

La base contiene los datos, no necesariamente los archivos externos apuntados por las URL de los perfiles. Las sesiones del navegador no se trasladan con el repositorio; volvé a iniciar sesión en el equipo nuevo.

## 7. Para un agente que continúe el trabajo

Leé [AGENTS.md](../AGENTS.md), [README.md](../README.md), [Arquitectura-Actual.md](Arquitectura-Actual.md) y [Busqueda-Avanzada.md](Busqueda-Avanzada.md). Revisá `git status`, las versiones y los puertos antes de iniciar. Conservá la SQLite existente: un inicio normal no requiere resetearla. Informá qué validaste realmente, especialmente si no ejecutaste Qwen, Linux o Docker.

Podés abrir la carpeta del repositorio en el agente y pedirle:

> Leé `AGENTS.md` y `docs/Guia-para-otro-equipo.md`. Prepará e iniciá Jobkler en este equipo, verificá el motor y una búsqueda avanzada, y contame el resultado. No subas modelos ni secretos y conservá los datos locales existentes.

Los informes `Arquitectura.md`, `backend/README.md` y `Informe-Busqueda-Avanzada-Local.md` contienen información histórica; las notas al comienzo de esos archivos apuntan a la documentación vigente.

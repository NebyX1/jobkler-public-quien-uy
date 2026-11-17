# Guía breve para agentes

Este repositorio es la demo local de Quien.uy: React/Vite, Flask, SQLite y búsqueda avanzada con Qwen local. Antes de modificar o iniciar el proyecto, leé [README.md](README.md), [la guía para otro equipo](docs/Guia-para-otro-equipo.md) y [la arquitectura vigente](docs/Arquitectura-Actual.md).

## Trabajar en este repositorio

- Revisá `git status` y conservá los cambios y datos que ya existan. Usá `rg` para localizar código y documentación.
- La API de dominio activa es Flask bajo `/api`; `src/data/db.json` aporta catálogos a la semilla, pero no es la base de perfiles que usa la aplicación. JSON Server y los documentos marcados como históricos no describen el arranque actual.
- El inicio normal es `./run.ps1 -NoWait` en Windows o `bash ./run.sh --no-wait` en Linux. Sus scripts preparan dependencias, base, índices y motor. Consultá la guía antes de ejecutar en otra plataforma o cambiar puertos.
- La base local `backend/instance/jobkler-demo.sqlite3`, las configuraciones `.env`, los logs, el caché ONNX y los procesos registrados son datos locales. No restablezcas la base ni termines procesos ajenos como parte de una comprobación rutinaria.
- Los modelos, los ejecutables de `ai-engine/bin/`, los secretos y las bases locales no se publican en Git. No imprimas claves ni las envíes al navegador. El modelo y el ejecutable se preparan por separado siguiendo la guía del motor.
- Tras cambiar código, ejecutá las comprobaciones pertinentes; `npm run verify` compila, ejecuta ESLint y corre las pruebas del backend una vez preparado `backend/.venv`. No afirmes que Qwen, Linux, Docker o un proveedor externo fueron probados si solo se usaron mocks o no se ejecutaron.
- Si cambian el arranque, los puertos, los contratos, los modelos o los flujos, actualizá la guía y los diagramas vigentes. Registrá los cambios relevantes en [CHANGELOG.md](CHANGELOG.md).

## Puntos de entrada

| Tema | Archivos principales |
| --- | --- |
| Arranque y parada | `run.ps1`, `stop.ps1`, `run.sh`, `stop.sh`, `scripts/prepare_local.py` |
| Motor Qwen y configuración | `ai-engine/engine.py`, `ai-engine/README.md`, `backend/app/config.py` |
| Búsqueda avanzada | `src/pages/AdvancedSearchPage.tsx`, `backend/app/api/advanced_search.py`, `backend/app/search/` |
| Datos demo e índices | `backend/app/seed_data.py`, `backend/app/search/expanded_fixtures.py`, `backend/app/search/documents.py`, `backend/app/search/indexer.py` |
| Validación | `backend/tests/`, `ai-engine/test/`, `npm run verify` |

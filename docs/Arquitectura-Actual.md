# Arquitectura actual de Quien.uy local

Esta guía describe la demo local actual. El informe [Arquitectura.md](../Arquitectura.md) describe una etapa anterior y se conserva como antecedente.

## Componentes y límites

```mermaid
flowchart LR
    Browser["Navegador"] -->|"HTTP :5173"| Vite["React + Vite"]
    Vite -->|"proxy /api"| Flask["Flask :5000"]
    Flask -->|"Bearer, /v1"| Qwen["llama.cpp + Qwen :8081"]
    Flask -->|"perfiles, sesiones y FTS5"| DB[("SQLite local")]
    Flask -->|"vectorizar consulta"| Embed["FastEmbed / MiniLM ONNX"]
    Embed -->|"vector de consulta"| Flask
    Flask -->|"ordenar candidatos relacionados"| Rerank["mMARCO MiniLM ONNX"]
    Worker["Worker de indexación"] -->|"trabajos y vectores"| DB
    Worker -->|"vectorizar fragmentos"| Embed
```

- Vite sirve la interfaz y redirige `/api` a Flask con el mismo origen del navegador. El navegador no llama a Qwen ni recibe su clave.
- Flask administra perfiles, reseñas, catálogos, sesiones y búsqueda. La fuente canónica es SQLite en `backend/instance/`; los contactos no se incluyen en los documentos de búsqueda.
- El catálogo resuelve pedidos simples de un oficio conocido. Qwen interpreta los demás mediante un objeto JSON validado. El encoder MiniLM calcula vectores para recuperar perfiles relacionados.
- El worker actualiza los fragmentos vectorizados fuera de la transacción que guarda el perfil. Los documentos FTS se sincronizan al escribir y se vuelven a comprobar por hash antes de mostrar resultados. FastEmbed es una biblioteca cargada por los procesos que la usan, no un servidor independiente.
- Los procesos se ejecutan en loopback. El modelo GGUF, el ejecutable de llama.cpp, el caché ONNX, los secretos, logs y la base no se versionan en Git.

## Arranque local

```mermaid
flowchart TD
    Inicio["run.ps1 / run.sh"] --> Config["Validar configuración y preparar claves"]
    Config --> Puertos["Comprobar puertos y dependencias"]
    Puertos --> Migrar["Migrar SQLite y aplicar semillas"]
    Migrar --> Indice["Sincronizar FTS y preparar encoder y reranker"]
    Indice --> Motor["Iniciar y comprobar Qwen autenticado"]
    Motor --> API["Iniciar Flask y comprobar readiness"]
    API --> Worker["Iniciar worker de embeddings si el encoder está listo"]
    Worker --> Web["Iniciar Vite y comprobar respuesta"]
    Web --> Lista["Aplicación local lista"]
```

Si el encoder no se prepara, el arranque continúa con recuperación semántica reducida. Con el motor administrado habilitado, un conflicto de puerto o la falta del modelo detienen el inicio con un diagnóstico. `stop.ps1` o `stop.sh` detienen los procesos registrados por Jobkler tras comprobar su identidad.

## Sesión y operaciones sobre perfiles

```mermaid
sequenceDiagram
    actor Persona
    participant Web as Navegador
    participant API as Flask
    participant DB as SQLite
    Persona->>Web: Elige una cuenta demo
    Web->>API: GET /api/auth/csrf
    API-->>Web: Token CSRF y cookie
    Web->>API: POST /api/auth/demo-login con CSRF
    API->>DB: Crea sesión con hash del token
    API-->>Web: Cookie de sesión HttpOnly y CSRF
    Web->>API: Consulta o escritura autenticada
    API->>DB: Comprueba sesión, CSRF y permisos
    API-->>Web: Datos o resultado de la operación
    Web->>API: POST /api/auth/logout con CSRF
    API->>DB: Revoca la sesión
```

La consulta pública de perfiles devuelve los publicados. Una cuenta autenticada puede crear hasta un perfil, y solo su propietaria puede editarlo, desactivarlo o borrarlo. Al guardar un perfil se actualiza el índice textual y se encola la indexación semántica. Las reseñas requieren sesión, CSRF y validaciones de autoría; la cuenta moderadora puede ocultarlas o publicarlas.

| Ruta | Uso principal |
| --- | --- |
| `GET /api/catalog` | Categorías, departamentos y localidades. |
| `GET /api/profiles` y `GET /api/profiles/{id-o-slug}` | Búsqueda y consulta pública de perfiles. |
| `POST /api/profiles`, `PATCH /api/profiles/{id}`, `DELETE /api/profiles/{id}` | Crear o administrar el perfil propio. |
| `POST /api/profiles/{id}/status` | Activar o desactivar el perfil propio. |
| `GET /api/reviews`, `POST /api/reviews` | Consultar o publicar reseñas. |
| `GET /api/auth/csrf`, `POST /api/auth/demo-login`, `POST /api/auth/logout` | Obtener CSRF, iniciar y cerrar sesión demo. |
| `POST /api/search/advanced` | Búsqueda avanzada autenticada. |
| `GET /api/health/ready` | Comprobar Flask y esquema SQLite; no certifica Qwen. |

## Búsqueda avanzada

```mermaid
sequenceDiagram
    actor Persona
    participant Web as React / Vite
    participant API as Flask
    participant LLM as Qwen local
    participant Texto as SQLite FTS5
    participant Vec as MiniLM + vectores
    participant Rerank as Reranker ONNX
    Persona->>Web: Envía un mensaje en el chat
    Web->>API: POST /api/search/advanced con sesión, CSRF y Accept NDJSON
    API->>API: Valida entrada, sesión y límite
    API-->>Web: Etapa de interpretación
    API->>LLM: Solicita interpretación JSON
    alt Qwen responde correctamente
        LLM-->>API: Servicio, acción, objeto y lugar
    else Qwen no está disponible o la respuesta es inválida
        API->>API: Extrae términos de forma determinista
    end
    API-->>Web: Etapa de ubicación
    API->>API: Resuelve la ubicación con el catálogo
    alt La ubicación está resuelta
        API-->>Web: Etapa de búsqueda de perfiles
        API->>Texto: Busca documentos elegibles con BM25
        Texto-->>API: Ranking textual
        API->>Vec: Vectoriza consulta y compara fragmentos vigentes
        Vec-->>API: Ranking semántico
        API->>API: Combina rankings y selecciona evidencia
        opt Sin coincidencias directas
            opt Sin citas candidatas válidas
                API->>LLM: Solicita una familia de servicios que abarque el pedido
                API->>Vec: Recupera perfiles con la reformulación
            end
            API->>Rerank: Ordena candidatos ampliados con el pedido original
            API->>LLM: Verifica citas literales de los primeros candidatos
            LLM-->>API: Referencias a citas aceptadas
            API->>API: Revalida perfil y cobertura de cada sugerencia
        end
        API-->>Web: Resultado con zona aplicada y perfiles o sugerencias
    else Hace falta aclarar la ubicación
        API-->>Web: Resultado con opciones cuando existen
    end
    Web-->>Persona: Respuesta dentro de la conversación
```

Qwen tiene un único turno de inferencia. Una consulta adicional espera hasta 10 segundos por defecto; si no consigue turno, recibe una respuesta recuperable. Los límites y el comportamiento detallado están en [Busqueda-Avanzada.md](Busqueda-Avanzada.md).

## Datos e indexación

```mermaid
flowchart LR
    Edicion["Alta o edición de perfil"] --> Tx["Transacción Flask"]
    Tx --> Perfiles[("profiles: fuente canónica")]
    Tx --> FTS[("documentos y FTS5")]
    Tx --> Cola[("trabajos de indexación")]
    Cola --> Worker["Worker persistente"]
    Worker --> Modelo["Encoder MiniLM ONNX"]
    Modelo --> Fragmentos[("fragmentos + vectores")]
    Perfiles --> Verificar["Validar estado y hash"]
    FTS --> Verificar
    Fragmentos --> Verificar
    Verificar --> Resultado["Resultado con evidencia"]
```

La semilla inicial crea 42 perfiles demo, nueve fixtures de búsqueda, 300 perfiles ampliados y 43 perfiles con tareas detalladas. En una base nueva hay 394 registros, de los cuales 388 comienzan activos. Los datos son ficticios y las semillas de población se aplican una vez.

## Ubicación del código

| Responsabilidad | Ubicación |
| --- | --- |
| Rutas y formularios | `src/router/`, `src/pages/AdvancedSearchPage.tsx` |
| Cliente HTTP y sesión | `src/api/client.ts`, `src/lib/auth.tsx` |
| API y políticas de sesión | `backend/app/api/`, `backend/app/services/sessions.py` |
| Contrato e interpretación Qwen | `backend/app/search/contracts.py`, `backend/app/search/llm.py` |
| Ranking, filtros y evidencia | `backend/app/search/engine.py`, `backend/app/search/catalog.py` |
| Índice y embeddings | `backend/app/search/documents.py`, `indexer.py`, `encoder.py`, `model_manifest.py` |
| Datos sintéticos | `backend/app/seed_data.py`, `backend/app/search/fixtures.py`, `expanded_fixtures.py` |
| Motor y procesos | `ai-engine/engine.py`, `run.ps1`, `run.sh`, `stop.ps1`, `stop.sh` |

## Autenticación y modos

La demo usa cuentas ficticias y sesiones de backend con cookie HttpOnly; las escrituras y la búsqueda avanzada requieren CSRF. FusionAuth es una configuración separada y no está validada aquí con credenciales reales. La búsqueda avanzada de esta entrega está restringida a la demo local autenticada; no se presenta como despliegue productivo.

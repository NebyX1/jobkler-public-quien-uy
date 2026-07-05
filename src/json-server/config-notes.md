# Notas de configuración

Documenta las decisiones de configuración de JSON Server para
Quien.uy, incluyendo puertos, variables de entorno, base de datos y
limitaciones conocidas.

---

## Datos básicos

| Concepto              | Valor                                  |
|-----------------------|----------------------------------------|
| Base de datos         | `src/data/db.json`                     |
| Puerto API            | `3001`                                 |
| Puerto frontend       | `5173` (Vite por defecto)              |
| Variable de entorno   | `VITE_API_BASE_URL`                    |
| URL esperada API      | `http://localhost:3001`                |
| URL esperada Vite     | `http://localhost:5173`                 |

---

## Variable de entorno del frontend

El frontend lee la URL de la API desde `import.meta.env.VITE_API_BASE_URL`.
El archivo [`src/config/api.ts`](../../config/api.ts) actúa como punto
único de configuración:

```ts
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:3001";
```

### Por qué se hace así

- **Configurable sin redeploy.** Cambiar de mock a staging es solo
  editar la variable de entorno y reiniciar Vite.
- **Cambio de puerto centralizado.** Si el puerto `3001` está ocupado,
  alcanza con tocar `.env` y `package.json` (script `dev:api`).
- **Sin hardcodes.** Ningún componente importa la URL literal; todos
  consumen `API_BASE_URL`.

### Archivos relacionados

- `.env.example` — variable de entorno plantilla (commiteable).
- `.env` — variable real por developer (NO commitear).
- `src/config/api.ts` — punto de lectura único en TypeScript.

---

## Scripts de `package.json`

```jsonc
{
  "scripts": {
    "dev:api": "json-server src/data/db.json --port 3001",
    "dev:all": "concurrently -k -n vite,api -c cyan,magenta \"npm run dev\" \"npm run dev:api\""
  }
}
```

### Por qué no usamos `--watch` en el script

`json-server@1.0.0-beta.15` cambió la CLI:

- **Antes (0.x):** `json-server --watch db.json --port 3001`
- **Ahora (1.x):** `json-server db.json --port 3001` — el watch es
  automático y el flag `--watch` ya no aparece en `--help`.

En este proyecto se usa la sintaxis de v1 para evitar warnings y
aprovechar el comportamiento nativo. Si alguien conserva una versión
0.x, el script sigue funcionando porque la v1 ignora silenciosamente
los flags desconocidos.

> Si ves `unknown option --watch`, significa que la versión instalada
> es 0.x. En ese caso, usá la sintaxis legacy y abrí un PR para
> actualizar.

---

## Estructura recomendada del directorio

```
src/json-server/
├── README.md        # arranque rápido
├── endpoints.md     # referencia de la API
└── config-notes.md  # este archivo
```

Archivos opcionales (sólo si se necesitan):

```
src/json-server/
├── routes.json      # aliases de rutas (ej. /api/* → /$1)
└── middleware.js    # middlewares personalizados
```

Para este proyecto **no son necesarios**:

- **`routes.json`** — la app consume la API directamente desde
  `http://localhost:3001/profiles`, sin prefijo `/api`. Agregar
  aliases sólo complicaría la configuración sin un beneficio real.
- **`middleware.js`** — no se necesita latencia artificial, auth mock
  ni logging todavía. Si se agrega en el futuro, debe documentarse en
  este archivo.

---

## Limitaciones de JSON Server

Conviene tener claras las restricciones de la herramienta para no
quedar atado a un mock que no escala.

- **Es un mock, no un backend real.** No usar en producción.
- **Filtros exactos.** No hay búsqueda full-text, no hay matching
  aproximado, no hay búsqueda insensible a acentos. Esto lo maneja
  hoy la capa de servicios del frontend
  (`src/services/profileService.ts`).
- **Sin auth real.** No hay usuarios, sesiones, ni permisos. Si se
  necesita auth mock, usar `middleware.js`.
- **Sin validación.** Acepta cualquier payload que coincida con el
  shape básico. Validar en cliente hasta tener un backend real.
- **Sin transacciones.** POST/PATCH/DELETE no son atómicos entre
  recursos. No simular lógica multi-recurso.
- **Sin paginación configurable por defecto.** JSON Server pagina en
  bloques de 10 elementos con `_page` y `_limit` (o `_per_page`).
  El frontend ya implementa paginación en cliente cuando hace falta
  (ver `profileService.ts`).

---

## Cuándo dejar JSON Server

Sustituir este mock cuando se presente cualquiera de estas señales:

1. La búsqueda debe ser real full-text (Elasticsearch, Meilisearch,
   Postgres `tsvector`, etc.).
2. La autenticación debe ser real (no mock).
3. Hay más de 1 developer levantando instancias y se necesita un
   estado compartido.
4. Empiezan a aparecer reglas de validación o lógica de negocio que
   no tiene sentido en el cliente.

En ese caso, mantener `src/services/profileService.ts` como **única**
puerta de acceso a datos del frontend, y reemplazar su implementación
por llamadas al nuevo backend. La interfaz de la capa de servicios
debería permanecer estable.

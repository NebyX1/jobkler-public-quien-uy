> **Guía histórica de un mock opcional.** El arranque actual de Jobkler usa Flask y SQLite para `/api`; no inicia JSON Server. Consultá la [guía vigente](../../docs/Guia-para-otro-equipo.md).

# JSON Server para Quien.uy

JSON Server se usa como **mock backend local** para Quien.uy durante el
desarrollo. Lee el archivo de base de datos

```
src/data/db.json
```

y expone una API REST completa (CRUD) sobre los recursos definidos ahí
(`profiles`, `categories`, `departments`, `localities`).

> ⚠️ Esto es **solo para desarrollo local** y datos mock. **No** es un
> backend de producción ni reemplaza a un servicio real con autenticación,
> autorización o validación.

---

## 1. Requisitos

- Node.js 18+
- La dependencia de desarrollo `json-server` ya está declarada en
  `package.json` (versión `^1.0.0-beta.15`).

Si por algún motivo la dependencia no estuviera instalada:

```bash
npm install -D json-server
```

> La beta `1.x` cambió la CLI: **ya no usa el flag `--watch`** (el watch
> es automático). Se documenta el cambio en
> [config-notes.md](./config-notes.md).

---

## 2. Comandos

### Levantar solo la API

```bash
npm run dev:api
```

Esto arranca JSON Server en `http://localhost:3001` leyendo
`src/data/db.json`.

### Levantar solo el frontend (Vite)

```bash
npm run dev
```

Vite queda en `http://localhost:5173`. El frontend consume la API usando
`VITE_API_BASE_URL` (ver `.env.example`).

### Levantar frontend + API en paralelo

```bash
npm run dev:all
```

Usa `concurrently` para correr ambos procesos con colores en la misma
terminal. `Ctrl+C` cierra los dos.

### Fallback manual (si los scripts no estuvieran disponibles)

Sintaxis oficial de json-server v1:

```bash
npx json-server src/data/db.json --port 3001
```

Sintaxis legacy (json-server 0.x) — **no usar en este proyecto**,
sólo se conserva en este README como referencia histórica:

```bash
npx json-server --watch src/data/db.json --port 3001
```

> Si la versión instalada ignora `--watch` silenciosamente, la API
> igualmente levanta. Si viera errores por flags desconocidos, usá la
> sintaxis de v1 de arriba.

---

## 3. URLs

| Recurso        | URL                                       |
|----------------|-------------------------------------------|
| Frontend Vite  | http://localhost:5173                     |
| API base       | http://localhost:3001                     |
| Profiles       | http://localhost:3001/profiles            |
| Categories     | http://localhost:3001/categories          |
| Departments    | http://localhost:3001/departments         |
| Localities     | http://localhost:3001/localities          |

---

## 4. CRUD automático

JSON Server genera CRUD completo para cada recurso de nivel superior del
archivo `db.json`. Por ejemplo, para `profiles`:

| Método   | Endpoint                | Descripción                          |
|----------|-------------------------|--------------------------------------|
| `GET`    | `/profiles`             | Listar todos los perfiles.           |
| `GET`    | `/profiles/:id`         | Obtener un perfil por `id`.         |
| `GET`    | `/profiles?slug=...`    | Buscar por `slug` (filtro exacto).   |
| `POST`   | `/profiles`             | Crear un perfil nuevo.               |
| `PUT`    | `/profiles/:id`         | Reemplazar un perfil completo.       |
| `PATCH`  | `/profiles/:id`         | Actualizar campos parciales.         |
| `DELETE` | `/profiles/:id`         | Eliminar un perfil.                  |

El detalle por recurso está en [endpoints.md](./endpoints.md).

---

## 5. Configuración

- Variable de entorno esperada por el frontend:
  `VITE_API_BASE_URL=http://localhost:3001`
- Archivo de configuración del frontend: `src/config/api.ts`
- Más detalles en [config-notes.md](./config-notes.md).

---

## 6. Troubleshooting

- **La API no responde.**
  Confirmá que `npm run dev:api` esté corriendo y que el puerto `3001`
  no esté ocupado por otro proceso.

- **Puerto 3001 ocupado.**
  Cambiá el puerto en el script `dev:api` de `package.json` y actualizá
  `VITE_API_BASE_URL` en `.env.example` / `.env` y en
  `src/config/api.ts`.

- **El frontend no se conecta a la API.**
  Verificá que `.env` exista y contenga
  `VITE_API_BASE_URL=http://localhost:3001`. Recordá reiniciar Vite
  después de cambiar variables de entorno (Vite las lee al arrancar).

- **CORS.**
  JSON Server habilita CORS abierto por defecto para desarrollo local,
  por lo que el frontend puede hacer `fetch` desde `localhost:5173` sin
  preflight adicional. Si ves errores de CORS, casi siempre se trata
  de un proxy mal configurado en `vite.config.ts` o de un `API_BASE_URL`
  mal escrito.

- **Cambios en `db.json` no se reflejan.**
  En la beta v1 el watch es automático, pero si la API no detecta los
  cambios, reiniciá `npm run dev:api`.

- **`SyntaxError` al arrancar.**
  Tu `src/data/db.json` no es JSON válido. Validá el archivo con
  `node -e "JSON.parse(require('fs').readFileSync('src/data/db.json','utf8'))"`.

- **`Cannot find module 'json-server'`.**
  Ejecutá `npm install` para asegurar que las dependencias estén
  instaladas.

---

## 7. Próximos pasos (futuro)

Si en el futuro el directorio crece (middlewares, rutas personalizadas,
auth mock, etc.), se sugiere mantener esta estructura:

```
src/json-server/
├── README.md          # este archivo
├── endpoints.md       # documentación de la API
├── config-notes.md    # decisiones de configuración
├── routes.json        # aliases de rutas (opcional)
└── middleware.js      # middlewares personalizados (opcional)
```

Nada de esto es necesario para que la app funcione hoy. Es sólo una
guía para cuando se necesite extender el mock backend.

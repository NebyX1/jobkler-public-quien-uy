# Endpoints de la API mock

Documentación de los recursos expuestos por **JSON Server v1** a partir
de `src/data/db.json`.

> URL base local: `http://localhost:3001`
>
> Todos los endpoints devuelven JSON. La API **no** valida ni aplica
> reglas de negocio: es un mock para desarrollo.

> ⚠️ **Importante — sintaxis de v1**
>
> JSON Server v1 (`1.0.0-beta.x`) cambió la API de query params respecto
> de v0:
>
> - Los filtros usan **`field:operator=value`** en lugar de `field=value`
>   plano (ej. `?featured:eq=true` en vez de `?featured=true`).
> - Los filtros de **boolean** deben usar `:eq=true` o `:eq=false`. Pasar
>   `?featured=true` sin operador matchea contra el string `"true"`, no
>   contra el boolean.
> - La paginación usa **`_per_page` + `_page`** (no `_limit`).
> - Las respuestas paginadas vienen envueltas en
>   `{ first, prev, next, last, pages, items, data: [...] }`.
> - La búsqueda full-text / acentos / filtros compuestos complejos se
>   manejan en el **cliente** desde
>   [`src/services/profileService.ts`](../../services/profileService.ts)
>   para no atarse a la sintaxis nativa de JSON Server.

---

## Profiles

### Listar todos

```http
GET /profiles
```

Por defecto JSON Server pagina en bloques de 10 (`_per_page=10`,
`_page=1`). Para traerse **todo** el array sin envolver en
`{ first, prev, ... }`, hay dos opciones:

1. **Traer el dataset completo (cliente):** la capa de servicios del
   frontend ya hace
   `fetchJson<Profile[]>('/profiles')` y filtra en memoria
   (ver `getProfiles` en `profileService.ts`).
2. **Pedir páginas grandes y concatenar:** `?_per_page=100&_page=1`,
   `?_per_page=100&_page=2`, etc. La app actual no lo necesita.

### Obtener por id

```http
GET /profiles/profile-001
```

### Filtros (sintaxis v1: `field:operator=value`)

```http
GET /profiles?featured:eq=true
GET /profiles?department:eq=Lavalleja
GET /profiles?locality:eq=Minas
GET /profiles?categoryId:eq=oficios
GET /profiles?slug:eq=ana-ferreira-psicologa-minas
```

Operadores disponibles:

| Operador      | Significado                                          |
|---------------|------------------------------------------------------|
| (ninguno)     | Igual a `eq`                                         |
| `:eq`         | Igual                                                |
| `:ne`         | Distinto                                             |
| `:lt`/`:lte`  | Menor que / menor o igual                            |
| `:gt`/`:gte`  | Mayor que / mayor o igual                            |
| `:in`         | Incluido en lista separada por comas                 |
| `:contains`   | String contiene (case-insensitive)                   |
| `:startsWith` | String comienza con (case-insensitive)               |
| `:endsWith`   | String termina con (case-insensitive)                |

> Se pueden combinar varios filtros en la misma query, pero **no** se
> pueden combinar condiciones OR/AND arbitrarias sin `_where`.

### Filtros booleanos

JSON Server v1 requiere `:eq` para booleanos:

```http
# Correcto en v1
GET /profiles?featured:eq=true

# No matchea con booleanos — matchea contra el string "true"
GET /profiles?featured=true
```

### Búsqueda libre con acentos (cliente)

La búsqueda insensible a acentos y la composición de filtros
multi-campo (profesión + departamento + localidad) **no las provee
JSON Server v1**. Las resuelve la capa de servicios del frontend
(`profileService.ts`), que trae todo el array y filtra en memoria
usando `normalizeText` y `matchesProfileSearch`.

```ts
import { getProfiles } from '@/services/profileService';

const results = await getProfiles({ q: 'psicologa' });
```

### Crear un perfil

```http
POST /profiles
Content-Type: application/json
```

```json
{
  "id": "profile-109",
  "slug": "nuevo-perfil-ejemplo-minas",
  "name": "Nuevo Perfil Ejemplo",
  "displayName": "Nuevo Perfil Ejemplo",
  "category": "Oficios",
  "categoryId": "oficios",
  "profession": "Electricista",
  "professionNormalized": "electricista",
  "department": "Lavalleja",
  "departmentId": "lavalleja",
  "locality": "Minas",
  "localityId": "minas",
  "shortDescription": "Servicio eléctrico residencial y comercial.",
  "description": "Atención en Minas y alrededores con presupuesto previo y respuesta rápida.",
  "photoUrl": "https://randomuser.me/api/portraits/men/10.jpg",
  "avatarFallback": "https://api.dicebear.com/10.x/initials/svg?seed=Nuevo%20Perfil",
  "phone": "099 000 000",
  "whatsapp": "59899000000",
  "email": "nuevo.perfil@example.com",
  "website": "",
  "instagram": "https://instagram.com/nuevoperfil",
  "address": "Centro, Minas",
  "serviceArea": ["Minas", "Lavalleja", "Online"],
  "tags": ["Instalaciones", "Mantenimiento", "Urgencias"],
  "availability": "Disponible",
  "verified": true,
  "rating": 4.7,
  "reviewsCount": 0,
  "yearsExperience": 5,
  "featured": false,
  "createdAt": "2026-07-03T00:00:00.000Z",
  "updatedAt": "2026-07-03T00:00:00.000Z"
}
```

### Actualizar parcialmente

```http
PATCH /profiles/profile-001
Content-Type: application/json
```

```json
{
  "availability": "No disponible",
  "updatedAt": "2026-07-03T12:00:00.000Z"
}
```

### Reemplazar completamente

```http
PUT /profiles/profile-001
Content-Type: application/json
```

(Enviar el objeto completo.)

### Eliminar

```http
DELETE /profiles/profile-001
```

### Paginación de listados

```http
GET /profiles?_page=1&_per_page=20
```

Respuesta:

```json
{
  "first": 1,
  "prev": null,
  "next": 2,
  "last": 6,
  "pages": 6,
  "items": 117,
  "data": [ /* ... 20 perfiles ... */ ]
}
```

---

## Categories

```http
GET /categories
GET /categories/oficios
GET /categories?id:eq=oficios
```

Estructura de cada item:

```json
{
  "id": "oficios",
  "name": "Oficios",
  "slug": "oficios",
  "description": "Electricistas, sanitarios, albañiles, carpinteros, pintores y más.",
  "icon": "Wrench",
  "featured": true,
  "sortOrder": 2
}
```

---

## Departments

```http
GET /departments
GET /departments/lavalleja
GET /departments?id:eq=lavalleja
```

Estructura:

```json
{
  "id": "lavalleja",
  "name": "Lavalleja",
  "slug": "lavalleja",
  "featured": true,
  "sortOrder": 8
}
```

---

## Localities

```http
GET /localities
GET /localities/minas
GET /localities?departmentId:eq=lavalleja
GET /localities?department:eq=Lavalleja
```

Estructura:

```json
{
  "id": "minas",
  "name": "Minas",
  "slug": "minas",
  "department": "Lavalleja",
  "departmentId": "lavalleja",
  "featured": true,
  "sortOrder": 1
}
```

---

## Convenciones generales

- Los `id` son **strings** en todos los recursos.
- Las relaciones se mantienen por id (`departmentId`, `localityId`,
  `categoryId`) y por nombre (`department`, `locality`, `category`)
  para tolerar distintos estilos de filtrado.
- Los recursos se exponen en plural (convención de JSON Server) y las
  rutas anidadas no son necesarias para esta app.
- `featured` es **boolean**. Filtrar con `:eq=true` o `:eq=false`.
- El recurso `_meta` del `db.json` existe como **objeto singular** y
  no debe ser filtrado ni mutado; queda accesible como
  `GET /_meta` pero no es parte del contrato de la app.

---

## Por qué el filtrado vive en el cliente

La capa de servicios del frontend (`src/services/profileService.ts`):

1. Hace `GET /profiles` (sin filtros server-side) y trae el array
   completo.
2. Aplica en memoria filtros por `q`, `department`, `locality`,
   `category`, `profession`, `featured`, `limit` y `page`.
3. Normaliza acentos y minúsculas antes de comparar.

Razones:

- JSON Server v1 no ofrece búsqueda insensible a acentos.
- Componer `q` + `department` + `locality` requiere varios query params
  manuales y no se traduce trivialmente a `:contains`.
- El dataset actual (`~117` perfiles) es chico y entra cómodo en
  memoria del cliente.
- Si en el futuro el dataset crece, **la única superficie a cambiar es
  `profileService.ts`** — el resto de la app no se entera.

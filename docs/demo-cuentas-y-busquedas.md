# Cuentas y consultas de demostración

Todas las cuentas, personas, perfiles y reseñas listadas aquí son ficticios. En la página de acceso, elegí una cuenta: el navegador no recibe permisos arbitrarios ni almacena la sesión en localStorage.

## Cuentas

| Opción de acceso | Recorrido |
| --- | --- |
| Cliente Demo | No tiene perfil al inicio; puede crear uno, consultar perfiles y publicar una reseña. |
| Prestadora A · Valentina Duarte Demo | Tiene un perfil de sanitaria en Minas; puede editar, desactivar, reactivar y eliminarlo. |
| Prestador B · Bruno Silva Demo | Tiene otro perfil en Solís de Mataojo; sirve para comprobar que no puede editar el de A. |
| Moderación Demo | Puede ocultar y volver a publicar reseñas desde la API moderada. |

Los fixtures tienen IDs estables en SQLite. Sus teléfonos, correo de contacto y enlaces externos están vacíos. El avatar muestra iniciales.

## Búsquedas esperadas

La API de búsqueda pagina en el servidor y solo devuelve perfiles activos.

| Consulta | Resultado esperado |
| --- | --- |
| termofones | Valentina Duarte Demo; Sandra Acuña Demo no aparece porque su perfil está inactivo. |
| calefones electricos | Bruno Silva Demo. |
| instalacion de programas | Camila Ferrer Demo. |
| rio negro o filtro rio-negro | Lucía Pereira Demo, en Fray Bentos. |
| categoría oficios + departamento Lavalleja | Coincidencias activas de oficios en Lavalleja; la paginación mantiene ambos filtros. |
| alarmas | El buscador común encuentra el texto de Pablo Castro Demo. El buscador léxico no interpreta que la descripción dice que no ofrece ese servicio. |

Para comprobar el detalle inactivo, iniciá sesión como Prestadora A y consultá GET /api/profiles/profile-006; como visitante debe responder 404.

## Límites de la prueba

La búsqueda es pública y textual. La normalización elimina diferencias de mayúsculas y tildes, pero no resuelve frases naturales, negaciones ni similitud semántica. No se usa ubicación GPS. La futura IA Qwen3.5-2B GGUF con llama.cpp en CPU queda deshabilitada hasta otra entrega y solo debería ofrecerse a usuarios autenticados.

# Cambios relevantes

## 2026-11-18

- La búsqueda avanzada prioriza coincidencias directas. Cuando faltan, amplía candidatos con la consulta original y reformulaciones de Qwen, usa mMARCO ONNX y verifica citas antes de mostrar hasta tres sugerencias.
- Se agregaron 43 perfiles ficticios con tareas detalladas y controles de exclusión, cobertura e inactividad. «Solís» ofrece Balneario Solís y Solís de Mataojo. Los títulos de mecánica automotor y automotriz coinciden con «mecánico».
- Se incorporaron pruebas del reranker, la semilla y la API, y 36 consultas etiquetadas para evaluar el recorrido con modelos reales.
- Se reemplazaron siete descripciones ficticias que anticipaban el caso de la cama por descripciones de habilidades generales. La instalación actualiza únicamente las fichas originales de esa semilla.
- La búsqueda puede reformular un pedido en términos de una familia de servicios. La evaluación comprueba la ausencia del objeto en el índice antes de medir casos de generalización.

- La búsqueda avanzada usa una interfaz de chat con historial temporal, ejemplos y etapas de progreso que llegan desde Flask.
- El chat aplica la ubicación reconocida en el mensaje, muestra la zona en los resultados y ofrece acciones para confirmar un lugar dudoso o ampliar la búsqueda a todo Uruguay.

## 2026-11-17

- Se incorporó `ai-engine/` para administrar Qwen3.5-2B con llama.cpp local, autenticación compartida con Flask, verificación de disponibilidad y parada del proceso registrado. Los pesos, binarios y secretos se preparan fuera de Git.
- Se agregaron 300 perfiles ficticios en diez categorías y 19 departamentos; 210 declaran una actividad adicional en su descripción. La semilla es de una sola aplicación y se indexa para búsqueda textual y semántica.
- La búsqueda avanzada espera hasta 10 segundos por el turno de inferencia y presenta el mensaje del servidor cuando está ocupado.
- Se documentaron la instalación desde cero, los flujos, la arquitectura vigente, los diagnósticos y las indicaciones para otros agentes. Los informes de una arquitectura anterior quedaron identificados como históricos.
- En el equipo de desarrollo se verificaron Windows, `npm run verify`, el contrato autenticado de Qwen y búsquedas reales, incluidas dos simultáneas. La instalación completa en otro equipo, Linux y Docker no se han validado de extremo a extremo en esta entrega.

## 2026-09-23

- Se implementó la búsqueda avanzada local y su índice híbrido. El [informe histórico](docs/Informe-Busqueda-Avanzada-Local.md) conserva las condiciones y resultados de ese momento.

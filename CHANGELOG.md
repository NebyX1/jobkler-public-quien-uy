# Cambios relevantes

## 2026-11-18

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

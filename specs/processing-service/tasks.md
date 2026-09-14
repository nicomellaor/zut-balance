# Tareas: servicio de procesamiento de cartolas

- [x] 1. Añadir las dependencias HTTP y multipart necesarias, sin cambiar las dependencias de la librería de ingesta.
  - Validación: instalación de desarrollo y `pytest` completados con 48 pruebas aprobadas.

- [x] 2. Crear la aplicación y `GET /health` con una respuesta no sensible.
  - Validación: prueba de endpoint recibe `200`; `pytest` pasa con 49 pruebas.

- [x] 3. Implementar `POST /v1/statements` con carga multipart de un único campo `file` y validación de presencia, cantidad, tipo y contenido vacío.
  - Validación: solicitudes inválidas devuelven errores estructurados `400`; `pytest` pasa con 53 pruebas.

- [x] 4. Aplicar los límites de `10 MiB` y `20` páginas antes de invocar el parser.
  - Validación: cargas que exceden cada límite devuelven `413`; `pytest` pasa con 55 pruebas.

- [x] 5. Integrar el parser soportado, serializar el `Statement` normalizado a JSON y mapear errores conocidos a respuestas seguras.
  - Validación: fixture aprobado devuelve el mismo JSON normalizado; errores de dominio devuelven `400` seguro; `pytest` pasa con 59 pruebas.

- [x] 6. Añadir el manejo seguro de fallos inesperados.
  - Validación: fallo simulado devuelve `500` seguro; `pytest` pasa con 59 pruebas.

- [x] 7. Documentar la ejecución y contrato HTTP en el README.
  - Validación: README documenta rutas, campo multipart, límites, respuestas y formato soportado; no promete persistencia ni formatos adicionales.

- [x] 8. Ejecutar la suite completa y verificar los criterios CA-01 a CA-10.
  - Validación: `pytest` pasa con 60 pruebas; reverificación independiente confirma CA-01 a CA-10 sin incumplimientos.

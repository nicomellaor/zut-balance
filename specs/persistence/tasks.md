# Tareas: persistencia de cartolas normalizadas

- [x] 1. Crear el repositorio SQLite, esquema versión 1 y conversiones entre filas y modelos normalizados.
  - Validación: pruebas temporales guardan y recuperan una cartola completa sin PDF ni texto extraído.

- [x] 2. Implementar integridad, deduplicación SHA-256, listado paginado y borrado en cascada.
  - Validación: pruebas confirman una sola cartola por huella, orden de movimientos, límites de listado y eliminación completa.

- [x] 3. Añadir configuración y API key segura a la aplicación, sin proteger `GET /health`.
  - Validación: rutas de datos rechazan credenciales ausentes o incorrectas antes de procesar la solicitud; health permanece público.

- [x] 4. Persistir `POST /v1/statements` y añadir rutas autenticadas de consulta, listado y borrado.
  - Validación: pruebas de API cubren creación, reutilización por huella, lectura, paginación, `404` y `204`; `pytest` pasa con 66 pruebas.

- [x] 5. Documentar configuración, privacidad, retención, deduplicación y contratos de persistencia.
  - Validación: README describe variables de entorno, API key, rutas y que SQLite requiere permisos restrictivos.

- [x] 6. Ejecutar suite completa y verificar CA-01 a CA-11.
  - Validación: `pytest` pasa con 66 pruebas; reverificación independiente confirma CA-01 a CA-11 sin incumplimientos.

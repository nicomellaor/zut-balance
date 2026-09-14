# Tareas: robustecimiento de persistencia SQLite

- [x] 1. Añadir validación no mutante del esquema v1 y errores de configuración.
  - Validación: bases nuevas y v1 válidas inicializan; variantes incompatibles no cambian datos ni versión.

- [x] 2. Añadir deduplicación con reintento acotado ante contención SQLite.
  - Validación: dos escrituras concurrentes de la misma huella devuelven un único registro persistido.

- [x] 3. Traducir agotamiento de contención a error HTTP estructurado seguro.
  - Validación: la API devuelve `503 database_busy` sin filtrar detalles SQLite, PDF ni credenciales.

- [x] 4. Completar pruebas de repositorio y API para esquemas incompatibles y concurrencia.
  - Validación: pruebas temporales cubren CA-01 a CA-07; suite completa pasa con 73 pruebas.

- [x] 5. Actualizar documentación operativa y ejecutar la suite completa.
  - Validación: README describe la incompatibilidad de esquema y `pytest` pasa con 73 pruebas.

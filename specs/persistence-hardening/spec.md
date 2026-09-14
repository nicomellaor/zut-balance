# Robustecimiento de persistencia SQLite

## Objetivo

Hacer segura y determinista la inicialización de SQLite y la deduplicación de
cargas concurrentes, sin alterar el modelo normalizado, la retención ni el
contrato HTTP de persistencia de la fase 4.

## Contexto

La fase 4 persiste cartolas normalizadas en SQLite y usa una restricción única
por SHA-256 para deduplicar PDFs. La revisión posterior identificó dos límites:
una base existente con tablas incompatibles puede marcarse como versión 1, y la
contención SQLite puede producir un bloqueo transitorio durante dos cargas del
mismo PDF. Este trabajo corrige esos límites antes de ampliar formatos.

## Alcance

- Validar la compatibilidad del esquema antes de establecer o aceptar
  `PRAGMA user_version = 1`.
- Rechazar una base con esquema Zut Balance incompleto, incompatible o de una
  versión futura sin modificarla.
- Mantener inicialización repetible para una base nueva o una base v1 válida.
- Resolver de forma acotada una contención transitoria al guardar dos cargas
  concurrentes con la misma huella.
- Devolver el registro existente para una carga concurrente idéntica cuando ya
  haya sido persistido.
- Cubrir estos comportamientos con pruebas temporales de SQLite y de API.

## Fuera de alcance

- Cambiar las tablas, campos, semántica de persistencia o `SCHEMA_VERSION = 1`.
- Migraciones hacia una versión de esquema nueva.
- Soportar motores distintos de SQLite, réplicas, colas o escrituras asíncronas.
- Reintentos ilimitados, reintentos de errores no transitorios o garantías de
  disponibilidad bajo contención sostenida.
- Cifrado, usuarios, múltiples API keys, retención automática o backups.

## Requisitos funcionales

### RF-01: Validación de esquema v1

Antes de tratar una base como v1, el repositorio debe comprobar que las tablas
`statements` y `transactions`, sus columnas requeridas, la unicidad de
`source_sha256` y la clave foránea con borrado en cascada están disponibles.

Una base vacía debe crear el esquema v1 completo y establecer su versión solo
después de crearlo correctamente. Una base v1 válida debe inicializarse de
forma repetible sin perder datos.

### RF-02: Rechazo seguro de bases incompatibles

Si una base tiene tablas de Zut Balance incompatibles, una versión futura o una
versión v1 sin el esquema requerido, la inicialización debe fallar mediante un
error explícito. No debe cambiar `user_version`, crear columnas parciales ni
modificar datos existentes.

### RF-03: Deduplicación bajo concurrencia

Dos solicitudes autenticadas concurrentes con los mismos bytes de PDF deben
converger en una única cartola y sus movimientos una sola vez. Si una solicitud
encuentra contención SQLite transitoria, puede reintentar durante un plazo
acotado y debe volver a consultar la huella antes de informar error.

Si la cartola ya fue creada por la solicitud competidora, ambas respuestas deben
devolver el mismo `statement_id`.

### RF-04: Preservación de contratos

Las rutas, códigos exitosos, autenticación, datos normalizados y política de no
guardar PDF o texto extraído definidos en la fase 4 deben mantenerse sin
cambios observables.

## Requisitos no funcionales

### RNF-01: Integridad

La validación y las escrituras deben usar transacciones y consultas
parametrizadas. Un error no puede dejar una cartola parcial, movimientos
huérfanos ni una versión de esquema que no corresponda a sus tablas.

### RNF-02: Determinismo y límites

Los reintentos deben estar limitados en cantidad o tiempo y aplicarse solo a
errores SQLite identificados como transitorios. El mismo estado de base debe
producir el mismo resultado de inicialización y deduplicación.

### RNF-03: Privacidad y seguridad

Los errores no deben incluir API keys, contenido del PDF, texto extraído ni
números de cuenta. No se deben añadir columnas que almacenen esos datos.

### RNF-04: Testabilidad

Las pruebas deben usar bases temporales y demostrar la ausencia de mutación en
esquemas incompatibles, la repetibilidad de v1 y la deduplicación concurrente.

## Criterios de aceptación

- **CA-01:** Una base nueva queda con el esquema v1 completo y `user_version`
  igual a 1.
- **CA-02:** Inicializar dos veces una base v1 válida conserva sus cartolas y
  movimientos.
- **CA-03:** Una tabla `statements` preexistente e incompatible causa un error
  explícito y no cambia la versión ni sus filas.
- **CA-04:** Una base con versión futura causa un error explícito sin mutación.
- **CA-05:** Una base marcada como v1 pero sin tablas, columnas, unicidad o FK
  requeridas causa un error explícito sin mutación.
- **CA-06:** Dos cargas concurrentes del mismo PDF producen una sola cartola,
  una sola colección de movimientos y el mismo `statement_id` en ambas
  respuestas.
- **CA-07:** Un bloqueo SQLite que excede el límite de reintento produce un
  error estructurado seguro y no datos parciales.
- **CA-08:** La suite existente de persistencia y API mantiene sus contratos de
  creación, consulta, listado, borrado, autorización y privacidad.

## Casos límite

- Base SQLite vacía con tablas ajenas que no usan nombres de Zut Balance.
- `statements` existente sin una columna requerida.
- `transactions` sin FK o sin `ON DELETE CASCADE`.
- Índice único de huella ausente.
- `user_version` igual a 0, 1 o superior a 1.
- La solicitud competidora inserta la huella entre la consulta inicial y el
  intento de inserción.
- Bloqueo SQLite transitorio y bloqueo que no se libera dentro del límite.

## Supuestos

- SQLite continúa siendo local y el directorio configurado existe y permite
  escritura.
- La concurrencia esperada es baja; un reintento acotado es suficiente para el
  proceso actual.
- La única huella por PDF sigue siendo el mecanismo de deduplicación válido.

## Preguntas abiertas

- ¿Qué versión de esquema y estrategia de migración se necesitarán al cambiar
  el modelo de datos en producción?
- ¿Cuándo justificará la carga de escritura migrar desde SQLite a PostgreSQL?

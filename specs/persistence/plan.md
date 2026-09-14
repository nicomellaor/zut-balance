# Plan técnico: persistencia de cartolas normalizadas

## Enfoque técnico

Se añadirá persistencia SQLite con `sqlite3` de la biblioteca estándar. Un
repositorio dedicado será responsable de inicializar el esquema, ejecutar las
transacciones y convertir entre filas SQLite y los modelos públicos inmutables.
La API mantendrá la validación y el parser existentes, pero autenticará las
rutas de datos antes de leer o procesar el archivo.

La configuración procederá exclusivamente de variables de entorno:

- `ZUT_BALANCE_DATABASE_PATH`: ruta del archivo SQLite.
- `ZUT_BALANCE_API_KEY`: secreto requerido en `Authorization: Bearer <key>`.

La aplicación se construirá mediante una factoría que reciba configuración para
pruebas. La exportación `app` para Uvicorn se conservará, pero sus rutas de
datos responderán con un error de configuración seguro si faltan las variables,
en vez de usar valores predeterminados inseguros.

`POST /v1/statements` calculará SHA-256 de los bytes ya validados y buscará una
cartola existente antes de procesarla. Para una huella nueva, procesará el PDF y
guardará cartola y movimientos en una transacción. Un conflicto de unicidad por
una solicitud concurrente volverá a leer el registro existente. No se guardan
bytes del PDF ni texto extraído.

## Componentes

| Ubicación | Cambio |
| --- | --- |
| `src/zut_balance/persistence.py` | Crear esquema SQLite, repositorio y conversiones de modelos. |
| `src/zut_balance/api.py` | Añadir factoría, configuración, autenticación y rutas de creación, consulta, listado y borrado. |
| `tests/test_persistence.py` | Probar repositorio SQLite, integridad, transacciones y ausencia de columnas prohibidas. |
| `tests/test_api.py` | Actualizar pruebas para API key y cubrir contratos persistidos. |
| `README.md` | Documentar configuración, autenticación, retención, deduplicación y rutas. |
| `docs/roadmap.md` | Marcar fase 4 como completada solo después de Verify `PASS`. |

## Modelo de datos

### `statements`

- `id`: UUID textual generado por la aplicación, clave primaria.
- `source_sha256`: SHA-256 hexadecimal del PDF, único.
- `created_at`: marca de tiempo UTC ISO 8601.
- Metadatos normalizados: banco, producto, cuenta enmascarada, moneda,
  período, número de cartola y paginación.
- Resumen: saldos de apertura/cierre, retenciones y saldo disponible.

### `transactions`

- `id`: entero SQLite, clave primaria.
- `statement_id`: clave foránea a `statements`, con borrado en cascada.
- `position`: posición documental, única junto a `statement_id`.
- Fecha, descripción, documento, canal, monto, tipo y saldo informado.

No existirán columnas para PDF, texto extraído ni cuenta sin enmascarar.

## Contrato HTTP

- `POST /v1/statements`: requiere API key; conserva la respuesta normalizada y
  agrega `statement_id`. Devuelve el mismo identificador para la misma huella.
- `GET /v1/statements/{statement_id}`: requiere API key; devuelve cartola
  completa o `404` seguro.
- `GET /v1/statements?limit=&offset=`: requiere API key; devuelve solo
  metadatos. `limit` por defecto 50 y máximo 100; `offset` por defecto 0.
- `DELETE /v1/statements/{statement_id}`: requiere API key; elimina cartola y
  movimientos, y devuelve `204`.
- `GET /health`: no requiere API key ni accede a datos.

Errores de autenticación, configuración, validación, ausencia y fallos internos
mantendrán el sobre seguro `{"error":{"code":"...","message":"..."}}`.

## Dependencias y decisiones

- No se añade ORM ni herramienta de migración: `sqlite3` permite una primera
  implementación pequeña y sin dependencias de producción adicionales.
- El esquema inicial se aplicará con `CREATE TABLE IF NOT EXISTS` y
  `PRAGMA user_version = 1`. Futuras versiones usarán migraciones explícitas
  condicionadas por esa versión.
- `secrets.compare_digest` compara la API key sin filtración temporal evitable.
- La API key se valida antes de leer multipart, contar páginas o invocar parser.

## Estrategia de pruebas

- Usar bases SQLite temporales por prueba.
- Probar guardar/cargar un `Statement`, orden de movimientos, listado y borrado
  en cascada.
- Simular una inserción fallida para demostrar rollback completo.
- Inspeccionar `PRAGMA table_info` para comprobar ausencia de columnas de PDF o
  texto.
- Probar API sin clave, clave incorrecta, clave válida, deduplicación, consulta,
  paginación, borrado y `GET /health` público.
- Verificar que la API conserva los datos normalizados y nunca revela API key ni
  cuenta sin enmascarar.
- Ejecutar toda la suite `pytest`.

## Riesgos y migraciones

- SQLite no cifra en reposo. El README exigirá permisos restrictivos del
  directorio y archivo; cifrado y manejo de claves quedan fuera de alcance.
- SQLite permite concurrencia limitada de escritura. Las transacciones cortas y
  la restricción única de huella resuelven la deduplicación correcta; si crece
  la carga, se evaluará PostgreSQL en una fase posterior.
- El hash permite reconocer una carga idéntica, pero no sustituye un modelo de
  identidad de usuario o tenant.
- La base de datos puede contener datos de fases futuras; los cambios de esquema
  deberán incrementar `PRAGMA user_version` y migrar sin pérdida.

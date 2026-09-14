# Plan técnico: robustecimiento de persistencia SQLite

## Enfoque técnico

Se mantendrá `sqlite3` y el esquema v1. Antes de crear o aceptar ese esquema,
el repositorio inspeccionará `PRAGMA user_version`, `sqlite_master` y las
pragmas de tablas/índices/FK necesarias. Solo una base sin tablas propias podrá
crear v1; una base v1 deberá pasar la misma validación. Cualquier discrepancia
generará un error de configuración sin ejecutar DDL ni cambiar la versión.

La deduplicación conservará la restricción única de `source_sha256`. El
repositorio distinguirá las excepciones SQLite transitorias de bloqueo, volverá
a consultar la huella entre reintentos limitados y reutilizará el registro que
haya creado la solicitud competidora. La API traducirá un agotamiento de ese
límite a su sobre de error seguro actual.

## Componentes

| Ubicación | Cambio |
| --- | --- |
| `src/zut_balance/persistence.py` | Validar esquema v1, clasificar contención transitoria y aplicar deduplicación con reintento acotado. |
| `src/zut_balance/api.py` | Convertir el error de persistencia agotado en respuesta estructurada sin detalles internos. |
| `tests/test_persistence.py` | Añadir casos de compatibilidad, no mutación y concurrencia del repositorio. |
| `tests/test_api.py` | Añadir el contrato seguro ante agotamiento de contención. |
| `README.md` | Documentar el fallo de inicio ante un esquema incompatible, si cambia el comportamiento operativo visible. |

## Modelo e interfaces

- `SCHEMA_VERSION` permanece en `1`; no se crea una migración.
- El repositorio expondrá un error de dominio de persistencia para distinguir un
  esquema incompatible o una contención agotada de un fallo inesperado.
- La validación verificará exactamente la estructura requerida por los métodos
  actuales, incluida la cascada que respalda `delete()`.
- El plazo y número de reintentos serán constantes privadas, finitos y cubiertos
  por pruebas; no se expondrán como configuración pública en esta fase.

## Decisiones

- No se reparará automáticamente una base incompatible: es más seguro rechazar
  que interpretar o modificar datos desconocidos.
- Se volverá a leer por SHA-256 antes y después de una colisión o bloqueo; la
  restricción única continúa como autoridad final.
- No se añadirán dependencias, ORM ni un worker de colas.

## Estrategia de pruebas

- Crear una base nueva y comprobar versión y estructura.
- Guardar una cartola, reinicializar y comprobar round-trip completo.
- Construir bases incompatibles con `sqlite3` y comprobar excepción, versión y
  filas sin cambios.
- Simular o coordinar dos conexiones concurrentes para la misma huella y
  comprobar una sola cartola y respuesta reutilizada.
- Simular un bloqueo no liberable para comprobar límite y respuesta HTTP segura.
- Ejecutar la suite completa `pytest`.

## Riesgos

- SQLite no ofrece alta concurrencia de escritura; los reintentos limitados
  mejoran la condición de carrera, no sustituyen una arquitectura de cola o un
  motor cliente-servidor.
- La inspección de constraints puede variar según SQLite; las comprobaciones se
  limitarán a las garantías que realmente usa el repositorio v1.

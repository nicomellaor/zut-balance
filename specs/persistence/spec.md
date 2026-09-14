# Persistencia de cartolas normalizadas

## Objetivo

Persistir de forma segura cartolas normalizadas y sus movimientos para permitir
su consulta y borrado posterior, sin conservar el PDF original ni texto
extraído.

## Contexto

Las fases 1 y 2 entregan cartolas normalizadas y validadas. La fase 3 las
expone mediante un servicio HTTP síncrono, pero descarta el resultado al
terminar cada solicitud. Esta fase incorpora persistencia local antes de añadir
nuevos formatos, categorización o una interfaz.

## Alcance

- Persistir cartolas y movimientos normalizados en SQLite local.
- Proteger las rutas que crean, consultan o eliminan datos mediante una API key
  única configurada en el entorno.
- Registrar una huella SHA-256 del PDF exclusivamente para reutilizar una carga
  idéntica sin duplicar los datos normalizados.
- Consultar una cartola completa por identificador y listar cartolas de forma
  paginada.
- Eliminar explícitamente una cartola y todos sus movimientos.
- Conservar datos normalizados hasta su eliminación explícita.
- Documentar la configuración, retención, contratos y controles de privacidad.

## Fuera de alcance

- Almacenar PDFs originales, texto extraído, archivos temporales o URL de
  descarga.
- Usuarios, OAuth, roles, múltiples API keys o aislamiento por tenant.
- Otros motores de base de datos, sincronización remota, replicación o copias
  de respaldo.
- Cifrado a nivel de base de datos o gestión de claves de cifrado.
- Otros bancos, productos, OCR, categorización, análisis, IA o interfaz.
- Borrado programado, períodos de retención automáticos y restauración de datos
  eliminados.

## Requisitos funcionales

### RF-01: Configuración y acceso

El servicio debe obtener la ruta SQLite desde `ZUT_BALANCE_DATABASE_PATH` y la
API key desde `ZUT_BALANCE_API_KEY`. Las rutas de datos deben requerir la API
key en `Authorization: Bearer <key>` y rechazar claves ausentes o incorrectas
sin revelar la clave esperada.

### RF-02: Modelo persistido

Cada cartola debe almacenar un identificador estable, huella SHA-256, fecha de
creación, metadatos normalizados, resumen financiero y movimientos en orden
documental. Cada movimiento debe conservar todos los campos del modelo público
`Transaction`.

No se debe almacenar el PDF, texto extraído, número de cuenta sin enmascarar ni
otro contenido no presente en el resultado normalizado público.

### RF-03: Creación e idempotencia

`POST /v1/statements` debe autenticar antes de procesar la cartola. Para una
carga válida no vista anteriormente, debe persistir la cartola y devolver el
resultado normalizado actual junto con `statement_id`.

Para la misma secuencia de bytes del PDF, debe reutilizar el registro existente
identificado por su SHA-256 y no crear filas adicionales de cartola o
movimientos.

### RF-04: Consulta

`GET /v1/statements/{statement_id}` debe devolver la cartola normalizada
completa almacenada, incluida su lista de movimientos, o un error estructurado
si no existe.

`GET /v1/statements` debe devolver una lista paginada de metadatos de cartolas,
sin movimientos, con límites explícitos de paginación.

### RF-05: Borrado

`DELETE /v1/statements/{statement_id}` debe eliminar la cartola y todos sus
movimientos en una única operación. Una consulta posterior del identificador
debe indicar que no existe.

### RF-06: Atomicidad e integridad

La creación de una cartola y sus movimientos debe ser atómica. Un error durante
la escritura no puede dejar cartolas parciales ni movimientos huérfanos.

La base de datos debe impedir huellas duplicadas y movimientos sin una cartola
existente.

### RF-07: Compatibilidad del servicio

`GET /health` debe seguir sin autenticación y sin revelar datos. Las respuestas
de procesamiento deben conservar `metadata`, `summary` y `transactions`; solo
pueden ampliar el contrato con `statement_id`.

## Requisitos no funcionales

### RNF-01: Privacidad

- El PDF y texto extraído no deben escribirse a SQLite.
- Las respuestas, errores y logs no deben exponer API keys ni números de cuenta
  sin enmascarar.
- La ruta de la base de datos debe documentarse como un archivo que requiere
  permisos restrictivos del sistema operativo.

### RNF-02: Seguridad

- La comparación de API keys debe evitar comparaciones sensibles al tiempo.
- Las consultas SQL deben usar parámetros, nunca interpolación de valores de
  entrada.
- La API key y ruta de base de datos no deben tener valores predeterminados
  inseguros.

### RNF-03: Fiabilidad y determinismo

- Las operaciones de creación, consulta, listado y borrado deben producir
  resultados deterministas para el mismo estado de base de datos.
- El esquema debe inicializarse de forma repetible y conservar la integridad de
  los datos existentes durante actualizaciones futuras.

### RNF-04: Testabilidad

- Las pruebas deben usar bases de datos temporales y fixtures sintéticos.
- Deben validar esquema, deduplicación, cascada, atomicidad, autorización y
  ausencia de campos prohibidos.

## Criterios de aceptación

- **CA-01:** Sin `ZUT_BALANCE_DATABASE_PATH` o `ZUT_BALANCE_API_KEY`, el
  servicio no inicia las rutas de datos con una configuración insegura.
- **CA-02:** Una solicitud autenticada válida crea una cartola, devuelve un
  `statement_id` y conserva el resultado normalizado del parser.
- **CA-03:** Una solicitud sin API key o con una clave incorrecta devuelve
  `401` con un error estructurado seguro y no procesa ni consulta datos.
- **CA-04:** Dos cargas del mismo PDF devuelven el mismo `statement_id` y dejan
  una sola cartola con sus movimientos una sola vez.
- **CA-05:** Una consulta autenticada por identificador devuelve exactamente los
  datos normalizados guardados; un identificador inexistente devuelve `404`
  seguro.
- **CA-06:** El listado autenticado devuelve solo metadatos paginados y respeta
  límites de `limit` y `offset` documentados.
- **CA-07:** El borrado autenticado elimina la cartola y sus movimientos; una
  consulta posterior devuelve `404`.
- **CA-08:** Un fallo de escritura no deja una cartola parcial ni movimientos
  huérfanos.
- **CA-09:** El esquema no contiene columnas para PDF original o texto extraído,
  y no devuelve más de cuatro dígitos de cuenta consecutivos.
- **CA-10:** `GET /health` sigue disponible sin API key y no expone datos.
- **CA-11:** README documenta variables de entorno, API key, retención, rutas
  de consulta/borrado, deduplicación y la necesidad de permisos restrictivos
  sobre SQLite.

## Casos límite

- Cabecera `Authorization` ausente, vacía, malformada o con esquema distinto de
  `Bearer`.
- Ruta SQLite inexistente cuyo directorio sí existe.
- Archivo SQLite existente sin el esquema de Zut Balance.
- Dos solicitudes simultáneas para el mismo PDF.
- Error durante la inserción de un movimiento.
- `limit` o `offset` ausentes, no numéricos, negativos o mayores que el máximo.
- Identificador de cartola inválido o inexistente.
- Borrado repetido del mismo identificador.

## Supuestos

- SQLite reside en almacenamiento local administrado por el entorno de
  despliegue y el proceso tiene permisos de lectura y escritura.
- Una única API key representa el acceso autorizado de esta primera versión.
- La SHA-256 del PDF puede persistirse para deduplicación aunque el archivo no
  se conserve.
- Los datos normalizados se mantienen hasta `DELETE` explícito.

## Preguntas abiertas

- ¿Cuándo se requerirá cifrado en reposo y cómo se administrarán sus claves?
- ¿Qué estrategia de migraciones será necesaria cuando exista una instalación
  con datos de producción?
- ¿Cuándo deberá evolucionar la API key única hacia usuarios y tenants?

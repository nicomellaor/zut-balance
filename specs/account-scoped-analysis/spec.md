# Análisis por ámbito de cuenta

## Objetivo

Permitir que consumidores de la API seleccionen un historial de análisis por una
identidad opaca de cuenta, en vez de elegir una cartola arbitraria como ancla.
El cambio debe ofrecer un catálogo deduplicado de cuentas analizables, conservar
la trazabilidad de las cartolas incluidas y evitar exponer números de cuenta como
identificadores de solicitud.

## Contexto

El análisis histórico actual recibe `anchor_statement_id` y deriva desde esa
cartola el historial compatible que comparte banco, producto, moneda y porción
visible de cuenta. Varias cartolas de la misma cuenta aparecen como opciones
equivalentes en la interfaz, aunque todas resuelven el mismo historial.

La API no posee una entidad pública de cuenta. Solo conserva números
enmascarados, por lo que la agrupación existente representa un ámbito compatible
y no una identidad bancaria infalible. Esta fase formaliza ese ámbito con un
identificador aleatorio persistente y reemplaza el contrato de cartola ancla.

Esta especificación reemplaza los requisitos de selección mediante
`anchor_statement_id` de `specs/historical-analysis/` y
`specs/analysis-signals/`. Mantiene sus reglas de compatibilidad, cobertura,
frontera compartida, solapamiento y señales.

## Alcance

- Incorporar una identidad opaca, estable y no derivable para cada ámbito de
  cuenta persistido.
- Asociar cada cartola almacenada a exactamente un ámbito de cuenta.
- Migrar datos existentes sin perder cartolas, movimientos, clasificaciones ni
  trazabilidad.
- Agrupar cartolas con identidad visible usando las reglas de compatibilidad
  vigentes.
- Mantener aislada cada cartola cuya cuenta sea ausente o completamente
  enmascarada.
- Exponer un catálogo autenticado de ámbitos de cuenta disponibles para análisis.
- Reemplazar `anchor_statement_id` por `account_id` en `GET /v1/analysis`.
- Añadir `account_id` al ámbito de la respuesta y conservar
  `scope.statement_ids` en orden cronológico.
- Resolver el historial completo o el rango opcional desde el ámbito elegido,
  sin truncamiento silencioso.
- Eliminar ámbitos vacíos cuando se elimina su última cartola.
- Actualizar pruebas y documentación del contrato incompatible.

## Fuera de alcance

- Conservar compatibilidad temporal con `anchor_statement_id`.
- Exponer el número de cuenta completo, usar el número enmascarado como
  identificador de URL o aceptar búsquedas por número de cuenta.
- Afirmar que una agrupación por últimos dígitos demuestra identidad bancaria.
- Extraer, almacenar o comparar el número de cuenta completo.
- Crear un fingerprint o HMAC del número completo, administrar un secreto para
  ello o intentar reconstruirlo desde datos existentes.
- Permitir unir o separar ámbitos manualmente.
- Cambiar fórmulas de análisis, categorización, comercios, recurrencias, avisos o
  highlights.
- Añadir usuarios, tenants o permisos por cuenta.
- Cambiar el diseño o comportamiento de la SPA; se realizará en la fase
  dependiente de flujo de análisis.

## Requisitos funcionales

### RF-01: Identidad de ámbito de cuenta

Cada ámbito debe tener un `account_id` aleatorio, opaco y estable. El valor no
debe contener ni permitir derivar banco, producto, moneda, número enmascarado,
hash de PDF o identificadores de cartola.

Cada cartola persistida debe pertenecer a exactamente un ámbito. Cargar otra
cartola con la misma identidad visible compatible debe reutilizar el ámbito
existente. Cargar una cartola sin dígitos visibles de cuenta debe crear un ámbito
aislado que no agrupe automáticamente otras cartolas ambiguas.

### RF-02: Migración de datos existentes

La inicialización de una base existente debe asignar un ámbito a todas sus
cartolas dentro de una migración atómica:

- cartolas con la misma tupla exacta de banco, producto, moneda y cuenta
  enmascarada con al menos un dígito visible comparten ámbito;
- cada cartola con cuenta ausente o sin dígitos visibles recibe un ámbito propio;
- movimientos y clasificaciones conservan sus relaciones y valores;
- un fallo deja la versión y los datos anteriores utilizables, sin migración
  parcial.

### RF-03: Catálogo autenticado

`GET /v1/accounts` debe devolver una lista determinista de ámbitos que poseen al
menos una cartola, ordenada primero por el período más reciente y con desempates
estables. Cada elemento debe incluir:

- `account_id`;
- banco y producto;
- moneda normalizada para presentación;
- número de cuenta enmascarado o `null`;
- estado de identidad visible o ambigua;
- cantidad de cartolas;
- inicio mínimo y término máximo de los períodos declarados.

El catálogo no debe aplicar el límite de paginación del historial de cartolas ni
duplicar un ámbito por cada PDF. Una instalación sin cartolas devuelve una lista
vacía.

### RF-04: Contrato de análisis por cuenta

`GET /v1/analysis` debe exigir exactamente un `account_id` y aceptar fechas
`from` y `to` opcionales. `anchor_statement_id` y `statement_id` dejan de ser
parámetros soportados y su presencia debe producir un error de solicitud.

Sin fechas, el análisis incluye todas las cartolas del ámbito. Con una o ambas
fechas, incluye únicamente cartolas cuyos períodos declarados intersectan el
rango inclusivo. Un rango sin historial disponible se rechaza explícitamente.

La respuesta debe incluir `scope.account_id`, `scope.statement_ids`,
`scope.from`, `scope.to`, moneda y versiones de reglas. Los identificadores de
cartola preservan la procedencia y el orden cronológico.

### RF-05: Compatibilidad y solapamiento

La resolución por `account_id` debe mantener como defensa las validaciones de
banco, producto, moneda y cuenta visible. Una frontera compartida continúa
siendo válida y un solapamiento real continúa rechazándose sin métricas
parciales.

El identificador opaco no autoriza mezclar cartolas incompatibles ni reemplaza
las verificaciones del dominio.

### RF-06: Eliminación

Eliminar una cartola debe actualizar inmediatamente el catálogo y los análisis
posteriores. Si el ámbito conserva otras cartolas, su `account_id` permanece
estable. Si se elimina la última cartola, el ámbito deja de existir y una
consulta posterior con ese identificador devuelve un error seguro de recurso no
encontrado.

### RF-07: Validación y errores

La API debe rechazar identificadores ausentes, duplicados o con formato inválido,
parámetros selectores obsoletos y fechas duplicadas o inválidas. Un ámbito
inexistente devuelve `404`; un rango sin historial devuelve `400`; un ámbito con
solapamiento o incompatibilidad devuelve `409`.

Los mensajes no deben reflejar identificadores recibidos ni revelar cuentas
completas, descripciones, hashes, SQL, rutas o secretos.

## Requisitos no funcionales

### RNF-01: Privacidad

Los identificadores de ámbito son datos pseudónimos y deben tratarse como datos
protegidos. No constituyen autorización. El catálogo y el análisis conservan la
autenticación actual y no exponen más información bancaria que el historial de
cartolas ya autenticado.

### RNF-02: Integridad y determinismo

Para el mismo estado persistido, el catálogo, la selección de cartolas y el
análisis deben ser deterministas. Consultar cuentas o análisis no modifica la
base de datos.

### RNF-03: Rendimiento

La resolución debe consultar solo cartolas del ámbito solicitado y, cuando hay
fechas, evitar cargar movimientos de cartolas que no intersectan el rango. No se
permite limitar silenciosamente la cantidad de cartolas o la extensión temporal.

### RNF-04: Migración y respaldo

La nueva versión de esquema debe validarse de forma estricta, rechazar versiones
futuras y mantener compatibilidad con el mecanismo de backup SQLite. Restaurar
una base migrada debe conservar cuentas, cartolas y análisis reproducibles.

## Criterios de aceptación

- **CA-01:** Dos cartolas existentes con identidad visible compatible migran al
  mismo `account_id`; cuentas visibles diferentes migran a ámbitos distintos.
- **CA-02:** Dos cartolas sin identidad visible migran a ámbitos aislados y nunca
  se agrupan automáticamente.
- **CA-03:** `GET /v1/accounts` devuelve una entrada por ámbito, con cantidad y
  extremos de período correctos, sin truncarse por la paginación de cartolas.
- **CA-04:** `GET /v1/analysis?account_id=...` analiza el historial completo o el
  rango solicitado y devuelve ese `account_id` junto con las cartolas incluidas.
- **CA-05:** `anchor_statement_id` y `statement_id` son rechazados; no existe una
  ruta de compatibilidad paralela.
- **CA-06:** Eliminar una cartola mantiene el ámbito mientras existan otras y
  elimina el ámbito cuando queda vacío.
- **CA-07:** Fronteras compartidas, huecos, meses parciales, solapamientos y
  señales conservan los resultados definidos por las fases anteriores.
- **CA-08:** Catálogo y análisis no exponen números completos, fingerprints,
  hashes de PDF ni detalles internos, y sus consultas no modifican SQLite.
- **CA-09:** Una migración fallida revierte completamente; una migración exitosa
  conserva todas las cartolas, movimientos y clasificaciones.
- **CA-10:** Las suites de dominio, persistencia, API, migración y backup pasan
  con el nuevo esquema y contrato.

## Casos límite

- Base vacía y base con una sola cartola.
- Más de cien cartolas de un mismo ámbito.
- Dos cuentas con el mismo banco y producto, pero distinta porción visible.
- Dos cuentas reales que podrían compartir los mismos últimos dígitos.
- Cuenta ausente, completamente enmascarada o con formato visible mínimo.
- Moneda ausente o no soportada.
- Cartolas cargadas fuera de orden, con huecos, frontera compartida o
  solapamiento real.
- Eliminación de una cartola intermedia y de la última cartola de un ámbito.
- `account_id` ausente, malformado, duplicado o inexistente.
- Rangos abiertos, invertidos, fuera del historial o que cruzan de año.
- Migración interrumpida y base con versión futura.

## Supuestos

- La agrupación compatible vigente continúa siendo suficiente para el producto
  local, aun cuando no sea una identidad bancaria criptográficamente fuerte.
- La SPA es el único consumidor conocido que debe adaptarse al reemplazo
  incompatible.
- La autenticación actual protege por igual catálogo y análisis.
- El identificador de ámbito permanece interno a una instalación y no necesita
  ser portable entre bases distintas.

## Preguntas abiertas

- No hay preguntas abiertas que bloqueen la planificación. Una identidad futura
  basada en información más fuerte requerirá una especificación separada de
  privacidad y administración de secretos.

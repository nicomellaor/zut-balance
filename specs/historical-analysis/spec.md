# Análisis histórico de cartolas

## Objetivo

Permitir analizar el historial disponible de una misma cuenta a partir de varias
cartolas compatibles. El análisis debe tratar una frontera mensual compartida
como continuidad normal, no como un solapamiento que inutiliza la agregación, y
debe conservar trazabilidad explícita de las cartolas incluidas y de la cobertura
efectiva.

## Contexto

El análisis actual exige que el consumidor enumere cartolas y rechaza todo par de
períodos inclusivos que se intersecta. Las cartolas mensuales de una misma cuenta
pueden terminar e iniciar en la misma fecha de cierre; por eso la regla actual
impide analizar secuencias históricas legítimas incluso cuando la cuenta es la
misma. El resultado es que la funcionalidad principal solo sirve para una
cartola aislada y no aporta trazabilidad temporal.

Esta fase reemplaza la definición de ámbito de la fase 7. La fase posterior de
señales de análisis cambia la comunicación de resultados, pero no forma parte de
esta fase. Cualquier rediseño de selección o presentación en la SPA queda fuera
de alcance por ahora.

## Alcance

- Resolver un ámbito histórico desde una cartola ancla de una cuenta compatible,
  sin requerir que el consumidor enumere manualmente cada PDF.
- Incluir por defecto todas las cartolas compatibles disponibles para la cuenta
  ancla con identidad visible, en orden cronológico, y permitir acotar ese
  historial mediante fechas inclusivas opcionales.
- Considerar continuidad válida que dos períodos consecutivos compartan solo su
  día de frontera: `anterior.period_end == siguiente.period_start`.
- Rechazar solapamientos reales de más de un día y ámbitos incompatibles.
- Informar en la respuesta las cartolas incluidas, el rango efectivo y cualquier
  hueco de cobertura ya calculado por el análisis.
- Mantener cálculos de gasto, categorías, meses, comercios y recurrencias sobre
  los movimientos de todas las cartolas aceptadas.
- Añadir pruebas sintéticas de historial, fronteras compartidas, huecos,
  incompatibilidades y alcance completo.

## Fuera de alcance

- Cambios de interfaz, flujo de selección, diseño móvil o presentación de
  resultados en la SPA.
- Cambiar categorías, reglas de comercio, fórmulas de métricas, persistencia,
  autenticación, retención o esquema SQLite.
- Deduplicación semántica de movimientos entre PDFs distintos mediante
  descripciones, montos, fechas, saldos o referencias.
- Ocultar, descartar o modificar movimientos de la fecha de frontera.
- Mezclar cartolas de cuentas claramente distintas, bancos, productos o monedas
  incompatibles.
- Truncar silenciosamente la historia de una cuenta para ajustarse a un límite.

## Requisitos funcionales

### RF-01: Ámbito histórico por cuenta

La API de análisis debe recibir exactamente un `anchor_statement_id` y resolver
el historial de su cuenta compatible. Este parámetro reemplaza la lista manual
de `statement_id`. Sin fechas explícitas, el ámbito incluye todas las cartolas
compatibles disponibles. Con `from` y/o `to`, el análisis usa el rango inclusivo
solicitado y conserva la lista completa de cartolas que aportan cobertura o
movimientos al rango.

La respuesta debe conservar `scope.statement_ids` como lista cronológica de las
cartolas efectivamente incluidas, además de `scope.from` y `scope.to` con el
rango efectivo. Una consulta no puede afirmar que analiza toda la historia si la
instalación la limita, omite o trunca.

Si el rango solicitado no intersecta el período declarado de ninguna cartola
compatible, la API debe rechazarlo como un rango sin historial disponible; no
debe incluir cartolas que no aportan cobertura para construir un ámbito ficticio.

### RF-02: Compatibilidad de cartolas

Dos cartolas pertenecen al mismo ámbito solo si banco, producto, moneda y la
misma porción visible de cuenta son iguales. Dos cuentas con porciones visibles
distintas no pueden combinarse. Una cartola con identidad ausente o completamente
enmascarada nunca se agrega automáticamente al historial de otra cuenta. Si se
usa como ancla, su ámbito contiene solo esa cartola.

### RF-03: Fronteras y solapamientos

Los períodos declarados siguen siendo inclusivos para validar movimientos y
calcular cobertura. Para formar un historial:

- `anterior.period_end < siguiente.period_start` es una separación válida; si
  hay días entre ambos, se informa un hueco de cobertura.
- `anterior.period_end == siguiente.period_start` es una frontera compartida
  válida y no se rechaza.
- `anterior.period_end > siguiente.period_start` es un solapamiento real y se
  rechaza sin calcular resultados parciales.

Una frontera compartida no elimina ni deduplica movimientos: cada movimiento
persistido de las cartolas aceptadas participa una vez por su procedencia. La
fase no inferirá igualdad de movimientos sin un identificador confiable.

### RF-04: Historial completo sin límites artificiales

El modo histórico debe cubrir todas las cartolas compatibles que correspondan al
ámbito solicitado, sin límites artificiales de cantidad de cartolas ni meses. La
API no puede devolver un subconjunto como si fuera el historial completo. Si una
futura capacidad técnica exige acotar el alcance, deberá definirse en una spec
nueva y responder con un error explícito.

### RF-05: Contrato y errores

El contrato recibe `anchor_statement_id` y fechas opcionales. La selección manual
por `statement_id` deja de ser un modo soportado. Si se envían fechas, deben ser
ISO 8601 y `from` no puede ser posterior a `to`.

Una frontera compartida válida devuelve `200`. Un solapamiento real, cuenta
incompatible o rango sin historial disponible devuelve un error seguro sin
modificar SQLite. Los errores no revelan cuentas completas, descripciones,
hashes de PDF, claves ni detalles internos.

## Requisitos no funcionales

### RNF-01: Integridad y trazabilidad

La resolución de ámbito y los resultados son deterministas para el mismo estado
persistido y los mismos parámetros. La respuesta permite identificar las
cartolas incluidas sin exponer sus hashes ni movimientos internos.

### RNF-02: Sin efectos secundarios

Resolver o consultar un historial no inserta, actualiza ni borra filas. Eliminar
una cartola afecta inmediatamente las consultas posteriores y su cobertura.

### RNF-03: Rendimiento explícito

La implementación debe evitar cargar o agregar cartolas ajenas al ámbito. Si el
historial compatible supera una capacidad acordada, el comportamiento debe ser
explícito, medible y documentado, nunca una omisión silenciosa.

### RNF-04: Testabilidad

Las reglas de compatibilidad, orden cronológico, frontera compartida, huecos,
solapamientos reales, rango opcional y errores deben probarse con cartolas y
SQLite temporales sintéticos.

## Criterios de aceptación

- **CA-01:** Dos cartolas de la misma cuenta con
  `period_end == period_start` pueden integrarse en un análisis histórico y sus
  movimientos se contabilizan según su procedencia persistida.
- **CA-02:** Dos cartolas con un solapamiento de dos o más días se rechazan sin
  devolver métricas parciales ni modificar SQLite.
- **CA-03:** Un historial con períodos separados produce huecos y meses parciales
  correctos, sin impedir el análisis de los períodos disponibles.
- **CA-04:** Una solicitud histórica sin fechas incluye todas las cartolas
  compatibles disponibles y declara exactamente cuáles participaron.
- **CA-05:** Las fechas opcionales acotan métricas y cobertura de forma inclusiva
  sin alterar los datos persistidos.
- **CA-06:** Un rango que no intersecta ninguna cartola compatible se rechaza sin
  devolver un ámbito ficticio ni modificar SQLite.
- **CA-07:** Cuentas visibles diferentes, banco/producto/moneda incompatibles e
  identidades ambiguas se rechazan de forma segura según RF-02.
- **CA-08:** El análisis histórico no aplica límites artificiales de cantidad de
  cartolas ni meses, ni devuelve una historia parcial como completa.
- **CA-09:** Pruebas de dominio, repositorio y HTTP cubren frontera compartida,
  cruce de año, huecos, solapamiento real, varias cuentas y eliminación.

## Casos límite

- Una sola cartola y una cuenta sin otras cartolas compatibles.
- Frontera compartida con movimientos en una o ambas cartolas.
- Períodos adyacentes sin fecha compartida.
- Períodos separados por uno o varios días, incluidos cruces de mes y año.
- Tres o más cartolas con una frontera compartida válida y un solapamiento real
  posterior.
- Cartolas cargadas fuera de orden cronológico.
- Una cuenta visible y otra totalmente enmascarada.
- Más de cien cartolas y rangos mayores a 24 meses.
- Eliminación de una cartola intermedia de un historial con cobertura continua.

## Supuestos

- Los períodos declarados por el banco continúan siendo inclusivos y representan
  cobertura disponible, aunque compartan su fecha de frontera.
- Una cartola distinta puede contener movimientos legítimos iguales en fecha y
  monto a otra; por eso esta fase no deduplica por heurísticas.
- Las clasificaciones persistidas siguen siendo la fuente de verdad de métricas.
- La autenticación existente protege el modo histórico igual que el análisis
  actual.

## Preguntas abiertas

- Si dos PDFs consecutivos incluyen el mismo movimiento de frontera, ¿qué
  producto o fuente autoritativa permitirá resolver esa duplicidad sin heurística?

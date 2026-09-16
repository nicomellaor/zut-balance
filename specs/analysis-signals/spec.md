# Señales estructuradas de análisis

## Objetivo

Reemplazar el contrato narrativo `insights` por señales estructuradas,
deterministas y no repetitivas. El backend debe comunicar límites de cobertura y
calidad de datos, junto con una única variación mensual destacada verificable,
sin duplicar las secciones de métricas, categorías, comercios o recurrencias.

## Contexto

La fase 9 añadió `insights` con títulos, texto libre, prioridades y evidencia
genérica. La SPA muestra esos textos antes de renderizar nuevamente los mismos
montos y rankings en el dashboard. Esto alarga el flujo, repite información y
mezcla advertencias importantes con observaciones que ya son visibles.

Esta fase sustituye el contrato backend de `insights`; no preserva compatibilidad
con ese campo. La SPA actual debe recibir una adaptación mínima en esta fase para
consumir tanto `anchor_statement_id` de la fase 10 como el contrato de señales y
permitir pruebas integradas. El rediseño visual amplio queda pospuesto.

## Alcance

- Eliminar `insights` de la respuesta de análisis y de su dominio asociado.
- Añadir `notices`, una lista de avisos estructurados sobre límites de
  interpretación de cobertura y calidad de datos.
- Añadir `highlights`, un objeto estructurado cuyo único highlight inicial es la
  mayor variación mensual disponible.
- Mantener todas las métricas existentes como la fuente de detalle para resumen,
  categorías, comercios y recurrencias.
- Mantener los resultados calculados al vuelo, sin texto generado, IA, red ni
  persistencia adicional.
- Añadir pruebas de dominio y HTTP del contrato reemplazado y de privacidad.
- Adaptar de forma mínima el cliente API y el flujo de análisis de la SPA al
  contrato anclado de fase 10 y a `notices`/`highlights`.
- Eliminar el renderizado del feed narrativo `insights` y mostrar los avisos y
  highlight recibidos sin recalcular hechos financieros.
- Extender pruebas de interfaz y E2E para validar la integración con el contrato
  nuevo.

## Fuera de alcance

- Rediseño visual amplio de frontend: jerarquía de dashboard, acciones de
  navegación, diseño móvil, tablas, gráficos o presentación contextual avanzada.
- Mantener compatibilidad HTTP con `insights`, migraciones aditivas o versiones
  paralelas del contrato.
- Párrafos, títulos, prioridades, evidencia con etiquetas libres, traducciones
  o decisiones de redacción por parte del backend.
- Recomendaciones financieras, causalidad, predicciones, presupuestos, puntajes
  de salud financiera o interpretación de una recurrencia como suscripción.
- Cambiar fórmulas de análisis, categorías, comercios, recurrencias, esquema
  SQLite, autenticación o retención.

## Requisitos funcionales

### RF-01: Sustitución de contrato

Toda respuesta exitosa de análisis debe contener `notices` y `highlights`, y no
debe contener `insights`. Los clientes que dependan de `insights` deben adaptarse
al nuevo contrato en la misma entrega; no se mantiene compatibilidad temporal.

### RF-02: Avisos de cobertura

`notices` debe incluir como máximo un aviso `incomplete_coverage` cuando
`coverage.gaps` no sea vacío o `coverage.partial_months` no sea vacío. El aviso
debe incluir:

- `kind: "incomplete_coverage"`;
- `severity: "warning"`;
- `gaps`, con los mismos límites ISO 8601 de `coverage.gaps`;
- `partial_months`, con los mismos valores `YYYY-MM` de cobertura.

No se genera este aviso cuando ambos conjuntos están vacíos.

### RF-03: Avisos de calidad de clasificación

`notices` debe incluir como máximo un aviso `limited_classification` cuando hay
gasto sin categoría, gasto sin comercio identificado o más de una versión de
ruleset. El aviso debe incluir:

- `kind: "limited_classification"`;
- `severity: "info"`;
- `uncategorized_amount` y `uncategorized_count`;
- `unidentified_merchant_amount` y `unidentified_merchant_count`;
- `ruleset_versions`.

Los valores deben reflejar directamente el resultado de análisis, aun cuando
alguno sea cero. No se genera el aviso cuando todos los límites anteriores están
ausentes: montos y cantidades de cobertura incompleta en cero y una única versión
de ruleset como máximo.

### RF-04: Highlight de variación mensual

`highlights.largest_monthly_change` debe ser `null` si no existe una variación
mensual con `absolute_change` distinto de `null` y de cero. En caso contrario,
debe identificar la variación con mayor valor absoluto; un empate se resuelve
con el mes actual más reciente.

El objeto debe contener:

- `previous_month`, `current_month`;
- `previous_amount`, `current_amount`;
- `absolute_change`;
- `percentage_change`, que conserva `null` cuando el análisis no puede
  calcularlo.

El highlight no declara causa, recomendación, tendencia futura ni juicio sobre
el gasto.

### RF-05: Orden, privacidad y coherencia

`notices` se ordena siempre: primero `incomplete_coverage`, luego
`limited_classification`. Los avisos y highlights solo usan hechos presentes en
el resultado de análisis y no exponen descripciones, números de cuenta, hashes,
identificadores internos, secretos, SQL ni datos de PDFs.

Una respuesta válida sin movimientos devuelve listas y objetos con valores
vacíos o nulos según estas reglas. Consultar señales no modifica SQLite.

### RF-06: Adaptación mínima de la SPA

El cliente de la SPA debe reemplazar la solicitud manual de múltiples
`statement_id` por `anchor_statement_id` y fechas opcionales. La vista de análisis
debe permitir elegir una única cartola ancla y enviar ese identificador; el
backend continúa resolviendo el historial compatible.

La SPA debe tipar `notices` y `highlights`, dejar de depender de `insights` y
mostrar los avisos recibidos junto al highlight mensual cuando exista. Esta
adaptación no recalcula montos, cobertura, clasificación ni variaciones, y no
incluye el rediseño visual amplio pospuesto.

## Requisitos no funcionales

### RNF-01: Determinismo

Para el mismo `AnalysisResult`, el generador de señales devuelve la misma forma,
orden y valores. No depende de reloj, red, IA, entorno ni estado externo.

### RNF-02: Contrato tipado

Cada `kind` tiene campos definidos por esta spec; el backend no entrega etiquetas
libres que obliguen a los clientes a adivinar unidades, formato o semántica.

### RNF-03: Testabilidad

Los avisos, el desempate de highlight, el contrato HTTP reemplazado, ausencia de
texto narrativo y privacidad deben probarse con resultados sintéticos y SQLite
temporal.

## Criterios de aceptación

- **CA-01:** Una respuesta de análisis contiene `notices` y `highlights`, y no
  contiene `insights`.
- **CA-02:** Huecos o meses parciales producen un único aviso de cobertura con
  exactamente sus rangos y meses de origen.
- **CA-03:** Gasto sin categoría, comerciantes no identificados o versiones
  mixtas producen un único aviso de calidad con valores consistentes con el
  resumen y el ámbito.
- **CA-04:** Sin límites de cobertura o clasificación, `notices` es una lista
  vacía.
- **CA-05:** El highlight usa la mayor variación absoluta disponible y el mes
  más reciente como desempate; no se genera para variación nula o no disponible.
- **CA-06:** La respuesta no contiene títulos, cuerpos, prioridades, texto
  generado ni evidencia de etiquetas libres del contrato anterior.
- **CA-07:** Avisos y highlight no revelan datos sensibles y consultar análisis
  no modifica SQLite.
- **CA-08:** Pruebas de dominio y API cubren avisos, ausencia de avisos, cero
  gasto, porcentajes nulos, desempates y contrato HTTP reemplazado.
- **CA-09:** Pruebas de interfaz y E2E demuestran que la SPA solicita análisis
  con una cartola ancla, no envía `statement_id`, no renderiza `insights` y puede
  presentar `notices` y `highlights` del contrato nuevo.

## Casos límite

- Sin movimientos con cobertura completa.
- Sin movimientos con huecos o meses parciales.
- Solo gasto sin categoría.
- Todo gasto sin comercio identificado.
- Varias versiones de ruleset sin gasto en el rango.
- Variación absoluta positiva, negativa, cero y no disponible.
- Dos meses con el mismo valor absoluto de variación.
- Gasto anterior igual a cero.
- Rango que cruza año y meses sin gasto.

## Supuestos

- `AnalysisResult` continúa siendo la fuente de verdad de señales.
- Montos de análisis se expresan como enteros CLP y meses como `YYYY-MM`.
- Esta fase limita la presentación frontend a la adaptación contractual mínima;
  una fase posterior decide la jerarquía y diseño final sin recalcular valores.
- Las secciones existentes de categorías, comercios y recurrencias continúan
  mostrando sus datos directamente, sin señales duplicadas.

## Preguntas abiertas

- ¿La señal de versiones mixtas debe incluir una versión de ruleset aunque no
  existan movimientos de gasto en el rango?
- No hay preguntas abiertas que bloqueen la planificación. La comunicación a
  consumidores externos del contrato incompatible y el rediseño amplio de la
  interfaz se tratarán en iniciativas posteriores.

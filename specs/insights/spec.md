# Insights deterministas de gastos

## Objetivo

Completar el alcance inicial de Zut Balance con explicaciones breves, en español
de Chile, sobre hechos ya calculados por el análisis determinista. Los insights
deben priorizar la calidad y cobertura de los datos antes de destacar patrones,
ser trazables a evidencia estructurada y no presentar recomendaciones ni
conclusiones financieras no verificables.

## Contexto

Las fases anteriores procesan cartolas PDF digitales compatibles, persisten
movimientos normalizados y clasificados, y calculan al vuelo cobertura, gasto,
evolución mensual, comercios principales y candidatos de recurrencia. La SPA
actual consume `GET /v1/analysis`, pero aún no presenta todas sus secciones.

Esta fase es el cierre del alcance inicial. El producto no requiere OCR para las
cartolas digitales soportadas: cuando un PDF no contiene texto extraíble o no
corresponde a un layout validado, se rechaza explícitamente. OCR queda fuera del
roadmap comprometido y solo podrá evaluarse como una iniciativa futura con
evidencia representativa de necesidad y precisión validable.

## Alcance

- Generar insights deterministas a partir de un `AnalysisResult` ya calculado,
  sin leer SQLite, PDFs, descripciones crudas ni estado externo.
- Añadir los insights como un campo aditivo de `GET /v1/analysis`.
- Devolver registros estructurados, ordenados y trazables con texto en español
  de Chile y evidencia numérica o temporal que la UI pueda presentar.
- Priorizar advertencias de cobertura y de calidad de clasificación antes de
  resúmenes o patrones de gasto.
- Mostrar en la SPA todas las secciones de análisis existentes y los insights,
  incluyendo sus estados vacíos y advertencias.
- Añadir pruebas unitarias, de contrato HTTP, de interfaz y E2E para los
  resultados observables de la fase.

## Fuera de alcance

- OCR, soporte de PDFs escaneados o de imágenes, fotografías u otros formatos
  bancarios.
- IA generativa, LLM, servicios remotos, modelos locales, prompts o credenciales
  de proveedores.
- Recomendaciones financieras, presupuestos, predicciones, puntajes de salud
  financiera, causalidad o juicios sobre la calidad de un gasto.
- Inferir comercio, categoría, ingreso, suscripción o intención desde una
  descripción cruda, signo, referencia o un dato no expuesto por el análisis.
- Cambiar reglas de categorización, versiones de ruleset, fórmulas de análisis,
  esquema SQLite, retención o autenticación.
- Persistir insights, crear endpoints separados, exportaciones o historial de
  explicaciones.

## Requisitos funcionales

### RF-01: Fuente y determinismo

El generador debe recibir únicamente un `AnalysisResult` y producir el mismo
conjunto, orden y contenido para una misma entrada. No debe consultar SQLite,
red, reloj, entorno, IA ni generar números que contradigan las métricas de
origen.

### RF-02: Contrato de insight

Cada insight debe incluir:

- `kind`: identificador estable de tipo.
- `priority`: entero positivo que define el orden de presentación.
- `title` y `body`: texto breve en español de Chile.
- `evidence`: lista no vacía de elementos con `label` y `value`, donde `value`
  es un dato ya presente o derivado determinísticamente de `AnalysisResult`.
- `caveat`: `null` o una advertencia breve que limite la interpretación.

Los montos en evidencia son enteros CLP sin formato de presentación; las fechas
usan ISO 8601 y los meses `YYYY-MM`. El contrato no puede exponer descripciones,
números de cuenta, hashes de PDF, identificadores internos de movimientos,
claves, secretos ni datos SQLite.

### RF-03: Tipos y condiciones de insights

El generador puede producir, como máximo, un insight de cada uno de estos tipos:

- `coverage_warning`: se produce si existen huecos o meses parciales. Debe
  identificar los rangos o meses afectados y advertir que no deben interpretarse
  como cobertura completa.
- `data_quality_warning`: se produce si hay gasto sin categoría, gasto sin
  comercio identificado o más de una versión de ruleset. Debe cuantificar la
  limitación aplicable y no afirmar completitud de categorías o comercios.
- `period_summary`: se produce siempre. Debe informar gasto y cantidad de
  movimientos; créditos y débitos excluidos se mantienen separados. Cuando no
  existe gasto, debe describir ese hecho sin sugerir que no hubo actividad fuera
  de la cobertura disponible.
- `monthly_change`: se produce solo si existe una variación mensual con cambio
  absoluto no nulo. Debe informar ambos meses y montos, el cambio absoluto y el
  porcentaje únicamente cuando está disponible. No debe atribuir una causa al
  cambio.
- `leading_category`: se produce solo para la categoría de gasto de mayor monto
  que no sea `sin_categoria`. Debe incluir monto y cantidad. Si empata, usa la
  categoría con valor canónico menor.
- `leading_merchant`: se produce solo si hay un comercio principal identificado.
  Debe indicar que el ranking cubre únicamente comercios identificados.
- `recurrence_candidate`: se produce solo si hay candidatos de recurrencia. Debe
  incluir comercio, cadencia, cantidad y rango de fechas observado; debe llamarlo
  candidato y nunca suscripción confirmada.

### RF-04: Priorización y desempates

La respuesta debe incluir a lo sumo cinco insights, seleccionados en este orden:
`coverage_warning`, `data_quality_warning`, `period_summary`, `monthly_change`,
`leading_category`, `leading_merchant`, `recurrence_candidate`. `priority`
empieza en uno y es consecutiva según el orden final.

Para `monthly_change`, se elige la variación con mayor valor absoluto de
`absolute_change`; en empate se elige el mes más reciente. Para
`recurrence_candidate`, se elige el primer candidato en el orden determinista
del análisis. Los tipos no seleccionados por el límite no se devuelven.

### RF-05: Contrato HTTP

Una respuesta exitosa de `GET /v1/analysis` debe añadir el campo `insights` como
lista, junto a las secciones existentes. La misma autenticación, validación de
ámbito y política de privacidad aplican antes de generar insights. Una consulta
válida sin movimientos responde `200` y contiene `period_summary`; puede además
incluir advertencias de cobertura o calidad que estén respaldadas por el
resultado.

### RF-06: Presentación de análisis e insights

La SPA debe presentar, además del resumen, categorías y evolución ya visibles:

- créditos, débitos excluidos, cobertura de categoría y cobertura de comercios;
- rangos cubiertos, huecos y meses parciales;
- variaciones absolutas y porcentuales, indicando valores no disponibles;
- comercios principales, con su limitación de cobertura;
- candidatos de recurrencia con fechas, estadísticas y lenguaje no conclusivo;
- los insights ordenados, su evidencia y `caveat` cuando exista.

Los estados sin movimientos, sin comercios, sin recurrencias y sin insights
opcionales deben ser explícitos. Los gráficos deben conservar una alternativa
textual o tabular equivalente y la interfaz debe seguir siendo usable en móvil,
escritorio y con teclado.

## Requisitos no funcionales

### RNF-01: Privacidad y seguridad

La fase no incorpora dependencias ni tráfico saliente. Los insights están sujetos
a la sesión web o Bearer existente y no amplían los datos sensibles expuestos por
el análisis.

### RNF-02: Resultados no persistidos

Generar o consultar insights no debe modificar SQLite. Eliminar una cartola debe
afectar de inmediato las explicaciones de solicitudes posteriores.

### RNF-03: Mantenibilidad y testabilidad

Las reglas de selección y redacción deben estar separadas del acceso HTTP y ser
unitariamente comprobables con resultados sintéticos. Los tipos, prioridades,
evidencia y lenguaje de seguridad forman parte del contrato probado.

## Criterios de aceptación

- **CA-01:** Para el mismo `AnalysisResult`, el generador devuelve exactamente
  los mismos insights, prioridades y evidencia, sin acceder a infraestructura ni
  persistir datos.
- **CA-02:** La respuesta de análisis añade `insights`, conserva las secciones
  existentes y no revela datos fuera de la política de privacidad.
- **CA-03:** Huecos y meses parciales generan una advertencia antes de cualquier
  interpretación de variaciones o patrones.
- **CA-04:** Gasto sin categoría, comercios no identificados y versiones mixtas
  de ruleset se declaran como límites de los datos, sin afirmar cobertura total.
- **CA-05:** Un cambio mensual usa únicamente una variación disponible, informa
  evidencia de ambos meses y no atribuye causalidad.
- **CA-06:** Categorías, comercios y recurrencias respetan sus condiciones,
  desempates y lenguaje definido; una recurrencia nunca se llama suscripción.
- **CA-07:** Nunca se devuelven más de cinco insights y el orden sigue RF-04.
- **CA-08:** La UI representa todas las secciones del análisis existente y los
  insights con evidencia, limitaciones y estados vacíos accesibles.
- **CA-09:** Las pruebas unitarias, HTTP, de interfaz y E2E cubren un caso con
  advertencias, un caso normal, cero gasto, desempates y candidatos recurrentes.
- **CA-10:** La documentación de roadmap declara la fase 9 como cierre del
  alcance inicial y OCR como iniciativa futura no comprometida.

## Casos límite

- Rango sin movimientos, con cobertura completa y con huecos totales.
- Meses parciales consecutivos y una variación mensual nula o no disponible.
- Mismo valor absoluto de variación en dos meses.
- Solo gasto `sin_categoria`, solo movimientos sin comercio y múltiples reglas
  de categorización persistidas.
- Empate entre categorías válidas y ausencia de categorías distintas de
  `sin_categoria`.
- Sin comercios identificados, más de diez comercios y candidatos recurrentes
  que no alcancen el límite de cinco insights.
- Candidato semanal o mensual válido, montos variables y nombre de comercio
  ausente.
- Montos grandes, fechas de fin de mes, cruce de año, vista móvil y navegación
  por teclado.

## Supuestos

- `AnalysisResult` y sus invariantes son la fuente de verdad para toda evidencia.
- Los montos de cartolas `PESOS` se presentan como CLP enteros.
- El español de Chile es el único idioma de la interfaz y contrato textual de
  esta fase.
- La cobertura y clasificación disponibles pueden ser incompletas; la ausencia
  de un insight opcional no implica la ausencia del hecho en los movimientos.

## Preguntas abiertas

No hay preguntas abiertas que bloqueen la planificación. La ampliación futura
del ruleset de comercios, OCR o una capa de redacción asistida por modelos
requerirá una especificación independiente.

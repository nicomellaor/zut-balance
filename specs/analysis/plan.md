# Plan técnico: análisis determinista de gastos

## Enfoque técnico

Se añadirá una capa de análisis pura que reciba cartolas ya persistidas y
clasificadas, más un rango inclusivo de fechas. Esta capa construirá un resultado
inmutable con resumen, cobertura, meses, comercios principales y candidatos de
recurrencia. No accederá a SQLite, HTTP, reloj ni red.

El repositorio entregará varias cartolas completas por sus identificadores sin
recalcular clasificaciones. La API validará autenticación y parámetros, cargará
el ámbito solicitado, verificará compatibilidad y solapamientos mediante la
capa de análisis, y serializará el resultado en `GET /v1/analysis`.

SQLite permanece en v2: el análisis se calcula al vuelo sobre `statements`,
`transactions` y `transaction_classifications`. No se añaden tablas, columnas,
índices ni cachés de métricas.

## Componentes

| Ubicación | Cambio |
| --- | --- |
| `src/zut_balance/analysis.py` | Crear modelos inmutables, validación de ámbito y cálculo puro de las métricas. |
| `src/zut_balance/persistence.py` | Añadir lectura completa de múltiples cartolas por `statement_id`, preservando clasificaciones materializadas. |
| `src/zut_balance/api.py` | Añadir `GET /v1/analysis`, validación de query y serialización segura. |
| `tests/test_analysis.py` | Crear fixtures sintéticos y pruebas unitarias de fórmulas, cobertura, ranking y recurrencias. |
| `tests/test_persistence.py` | Probar la lectura de múltiples cartolas, incluidos identificadores faltantes. |
| `tests/test_api.py` | Probar autenticación, contrato, validaciones, errores y resultados vacíos. |
| `README.md` | Documentar la ruta de análisis y sus límites al completar Verify. |
| `docs/roadmap.md` | Marcar fase 7 completada solo después de Verify `PASS`. |

## Modelo e interfaces

### Entrada de análisis

- `Statement` enriquecido con una `Classification` persistida por cada
  `Transaction`.
- Identificadores de cartola, requeridos para informar el ámbito pero no para
  revelar identificadores internos de movimientos.
- Fechas `from` y `to` como `date`, inclusivas.

### Resultado puro

El módulo definirá dataclasses inmutables para expresar, como mínimo:

- Ámbito: IDs solicitados, rango, moneda expuesta y versiones de ruleset.
- Cobertura: rangos cubiertos, huecos y meses parciales.
- Resumen: gasto, cantidades, créditos, débitos excluidos, cobertura de
  clasificación y cobertura de comercio.
- Mes: clave `YYYY-MM`, gasto, cantidad, desglose de categorías y variaciones
  opcionales.
- Comercio principal: clave, nombre, monto y cantidad.
- Candidato recurrente: comercio, cadencia, evidencia de fechas y montos, y
  estadísticas enteras.

La API convierte estos modelos a JSON y expone solo los campos especificados.
`merchant_key` puede usarse internamente para agrupar y desempatar, pero no se
incluye en la respuesta HTTP salvo que una futura especificación lo requiera.

### Lectura del repositorio

Se añadirá una operación de solo lectura que reciba IDs y devuelva las cartolas
completas encontradas con sus clasificaciones. La capa API conserva el orden de
los IDs solicitados y rechaza cualquier ID faltante. Las operaciones actuales de
lectura individual, deduplicación y borrado no cambian.

## Decisiones técnicas

- Las categorías incluidas y excluidas se definen una vez en `analysis.py`.
  Solo los débitos incluidos cuentan como gasto; créditos, transferencias,
  retiros e ingresos no se netean ni se convierten en otra clase.
- La cobertura se deriva de `period_start` y `period_end` de las cartolas, no de
  la presencia de movimientos. Se recorta al rango solicitado y se fusionan
  rangos adyacentes; un día sin rango cubierto es un hueco.
- Las cartolas se rechazan antes de agregar cuando sus períodos inclusivos se
  intersectan. Dos períodos adyacentes no se solapan.
- Los meses de respuesta abarcan todos los meses calendario tocados por el
  rango solicitado. Un mes es completo solo si su intervalo calendario íntegro
  queda cubierto; los meses de borde siempre son parciales cuando el rango no
  coincide con sus límites.
- Las variaciones usan solo meses consecutivos de la respuesta. Son nulas si
  falta cobertura completa en cualquiera de los dos meses o si el denominador
  es cero. Para porcentaje se usará aritmética decimal con redondeo explícito a
  dos decimales, sin usar `float`; los montos continúan como enteros.
- Rankings y recurrencias incluyen únicamente débitos de gasto con
  `merchant_key`. El ranking limita a diez filas y aplica el orden de la
  especificación. La salida no incluye descripciones crudas.
- La recurrencia ordena cada grupo por fecha. Una secuencia necesita tres o más
  fechas y todos sus intervalos deben satisfacer semanal o mensual, no ambas.
  El cálculo mensual ajusta el día esperado al último día del mes. Los
  promedios se redondean al entero más cercano con una política explícita y
  probada.
- Las clasificaciones persistidas son hechos históricos: se informan sus
  versiones, pero no se reejecuta el ruleset.
- Se conservará el sobre de errores seguro existente. La API usará errores de
  cliente distinguidos para parámetros inválidos, cartolas faltantes y ámbito
  incompatible o solapado, sin revelar datos de cartolas no autorizadas.

## Contrato HTTP

La ruta autenticada será:

```text
GET /v1/analysis?statement_id=<uuid>&statement_id=<uuid>&from=YYYY-MM-DD&to=YYYY-MM-DD
```

- `statement_id`: requerido, repetible, único, entre 1 y 100 valores.
- `from` y `to`: requeridos, ISO 8601 de fecha, inclusivos y con duración de
  hasta 24 meses calendario.
- Éxito: `200` con `scope`, `coverage`, `summary`, `monthly`,
  `top_merchants` y `recurrence_candidates`.
- Consulta válida sin movimientos: `200`, importes y cantidades cero, y listas
  vacías donde corresponda.
- Parámetros inválidos o IDs repetidos: `400`.
- Cartola inexistente: `404` sin indicar qué otro ID pudo ser válido.
- Ámbito incompatible, ambiguo o con períodos solapados: `409`.
- Falta o fallo de autenticación: `401`, antes de acceder al repositorio.

## Estrategia de pruebas

- Construir cartolas y movimientos sintéticos con clasificaciones explícitas;
  no ampliar fixtures PDF ni usar información financiera real.
- Probar inclusiones/exclusiones de gasto, créditos, `sin_categoria`, sumas y
  cobertura de comercios.
- Probar límites inclusivos, meses vacíos, cruces de año, rangos parciales,
  huecos y cobertura completa.
- Probar cambios positivos y negativos, denominador cero, ausencia de cobertura
  y redondeo porcentual decimal.
- Probar agrupación por `merchant_key`, límite diez, empates y ocultación de
  descripciones.
- Probar recurrencias semanales, mensuales, fin de mes, tolerancias, montos
  variables, menos de tres apariciones e intervalos irregulares.
- Probar cuentas, bancos, productos y monedas incompatibles, cuenta ambigua,
  IDs repetidos, ID faltante y solapamiento inclusivo de períodos.
- Probar respuesta HTTP autenticada, errores seguros, respuesta vacía, ausencia
  de campos sensibles y que borrar una cartola modifica el resultado siguiente.
- Ejecutar la suite completa y Verify contra CA-01 a CA-10.

## Riesgos y migración

- No hay deduplicación semántica entre cartolas distintas. Rechazar
  solapamientos evita doble conteo, pero no resuelve movimientos duplicados en
  períodos no solapados; queda fuera del alcance.
- La cuenta enmascarada es una señal limitada. El rechazo de ámbitos ambiguos
  evita combinar cuentas que no se pueden identificar de forma segura.
- El ruleset v1 reconoce pocos comercios. Los rankings y recurrencias pueden ser
  poco poblados, pero no deben sustituirse con agrupación de descripciones.
- Las cartolas con diferentes versiones de reglas se aceptan como snapshots
  históricos y declaran sus versiones en la respuesta.
- La fase no requiere migración. Si el volumen futuro exige índices o métricas
  materializadas, será una fase separada con esquema v3, invalidación por
  borrado y pruebas de migración atómica.

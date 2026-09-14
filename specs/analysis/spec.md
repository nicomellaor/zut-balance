# Análisis determinista de gastos

## Objetivo

Entregar métricas reproducibles sobre movimientos categorizados de cartolas
seleccionadas explícitamente: gasto de consumo, cobertura de clasificación,
evolución y variación mensual, comercios principales y candidatos de
recurrencia. Los resultados deben preservar las limitaciones conocidas de los
datos en vez de inferir hechos financieros no verificables.

## Contexto

La fase 6 persiste cartolas, movimientos y una clasificación determinista por
movimiento en SQLite v2. La fase 7 añade la capa de análisis del roadmap antes
de una interfaz o insights asistidos. Las cartolas solo se deduplican por la
huella exacta de sus bytes: cartolas distintas pueden representar períodos
solapados y no deben agregarse silenciosamente.

## Alcance

- Calcular métricas al vuelo para cartolas identificadas explícitamente y un
  rango de fechas inclusivo.
- Definir gasto de consumo como débitos en `alimentacion`, `transporte`,
  `salud`, `entretenimiento`, `hogar`, `servicios`, `compras`, `comisiones` y
  `sin_categoria`.
- Informar créditos y débitos excluidos (`transferencias`, `retiros` e
  `ingresos`) por separado, sin compensarlos contra gasto.
- Exponer un resumen, desglose por categoría, cobertura de datos, evolución y
  variación mensual, comercios principales y candidatos recurrentes.
- Exponer las métricas mediante `GET /v1/analysis`, protegido por la misma API
  key que las rutas de cartolas.
- Rechazar ámbitos ambiguos, cartolas incompatibles y períodos de cartolas que
  se solapan.

## Fuera de alcance

- Persistir métricas, tendencias, resultados de recurrencia o datos derivados.
- Modificar SQLite v2, reclasificar movimientos o alterar clasificaciones
  persistidas.
- Deduplicar semánticamente movimientos entre PDFs distintos o fusionar
  cartolas solapadas.
- Conversión de moneda, tipos de cambio, saldos, presupuestos, predicciones,
  recomendaciones financieras, IA o puntajes de confianza.
- Inferir devoluciones, ingresos o comercios desde signo, descripción cruda o
  referencias de transferencias.
- Exponer descripciones, números de cuenta, hashes de PDF, identificadores
  internos de movimientos o contrapartes de transferencias en métricas.
- Endpoints de listado o filtrado de movimientos.

## Requisitos funcionales

### RF-01: Selección y compatibilidad del ámbito

`GET /v1/analysis` debe recibir entre una y cien ocurrencias únicas de
`statement_id`, y los parámetros `from` y `to` en ISO 8601 de fecha. El rango
es inclusivo, `from` no puede ser posterior a `to` y no puede abarcar más de 24
meses calendario.

Todas las cartolas seleccionadas deben existir y tener el mismo banco, producto
y moneda. Para seleccionar más de una cartola, sus cuentas enmascaradas deben
coincidir y contener una porción visible que permita distinguirlas; una cuenta
ausente o completamente enmascarada hace el ámbito ambiguo. La moneda inicial
soportada es `PESOS`, que se expone como `CLP`; una moneda nula, desconocida o
mezclada se rechaza.

Los períodos inclusivos declarados por dos cartolas seleccionadas no pueden
intersectar, incluso si dentro de la intersección no hay movimientos.

### RF-02: Resumen de gasto y cobertura de clasificación

El resumen debe incluir `spending_amount` y `transaction_count` calculados solo
con movimientos de débito en las categorías de gasto de consumo del alcance.
Debe incluir por separado `credits_amount`, `credits_count`,
`excluded_debits_amount` y `excluded_debits_count`.

El desglose por categoría debe contener, para cada categoría de gasto presente,
su monto y cantidad. `uncategorized_amount` y `uncategorized_count` deben
informar la porción de gasto con categoría `sin_categoria`; estos movimientos
siguen incluidos en `spending_amount`. No se debe usar el saldo de la cartola o
el saldo informado de una fila para calcular gasto.

La respuesta debe incluir cobertura de comercios: monto y cantidad de gasto con
`merchant_key` conocido, y monto y cantidad sin comercio identificado.

### RF-03: Cobertura temporal y evolución mensual

La respuesta debe informar los rangos de cartola que cubren el rango solicitado,
los huecos sin cobertura y los meses parciales. Un mes es parcial si el rango
solicitado o los períodos de cartola disponibles no cubren todos sus días.

La evolución debe agrupar los movimientos de gasto por mes calendario según la
fecha del movimiento, incluyendo meses sin gasto dentro del rango solicitado.
Cada mes debe incluir monto, cantidad y desglose por categoría.

### RF-04: Variaciones mensuales

Cada mes posterior al primero debe comparar su gasto con el mes calendario
anterior devuelto. Debe informar `absolute_change` y `percentage_change`.
`absolute_change` es el monto actual menos el anterior. `percentage_change` se
calcula como `(actual - anterior) / anterior * 100`, redondeado a dos decimales.

La variación porcentual debe ser `null` si el monto anterior es cero. Ambos
campos de variación deben ser `null` si el mes actual o el anterior no tiene
cobertura completa. El primer mes no tiene variación.

### RF-05: Comercios principales

Los comercios principales deben usar solo movimientos de gasto con
`merchant_key` persistido. Se agrupan por `merchant_key` y se presentan con su
`merchant_name` canónico, sin usar descripciones originales como identidad.

El resultado debe contener como máximo diez comercios. El orden es monto total
descendente, cantidad de movimientos descendente y `merchant_key` ascendente.
Cada comercio incluye monto y cantidad. Los movimientos sin comercio no deben
aparecer en este ranking y sí deben estar reflejados en la cobertura de
comercios.

### RF-06: Candidatos de recurrencia

Un candidato recurrente debe corresponder a débitos de gasto con el mismo
`merchant_key`, al menos tres ocurrencias dentro del rango y una única cadencia
válida en todos sus intervalos consecutivos.

- Cadencia semanal: cada intervalo es de 7 días con tolerancia de 2 días.
- Cadencia mensual: cada ocurrencia corresponde al mismo día del mes que la
  anterior, ajustado al último día del mes cuando sea necesario, con tolerancia
  de 3 días.

El monto puede variar. Un candidato debe devolver comercio, cadencia, fechas,
montos, cantidad, monto mínimo, promedio redondeado al peso más cercano y monto
máximo. Las secuencias con menos de tres ocurrencias, intervalos irregulares o
más de una cadencia no se devuelven. El resultado no debe expresar confianza ni
llamar a un candidato una suscripción confirmada.

### RF-07: Contrato HTTP y privacidad

La respuesta exitosa debe contener `scope`, `coverage`, `summary`, `monthly`,
`top_merchants` y `recurrence_candidates`. `scope` debe informar los
`statement_id` solicitados, rango, moneda y versiones de ruleset representadas.
Las versiones de ruleset persistidas son autoritativas y no se recalculan.

Una consulta válida sin movimientos debe responder `200` con totales cero y
listas vacías. Las entradas inválidas deben usar el sobre de error existente.
Las rutas sin autenticación válida deben responder antes de consultar datos. Las
respuestas y errores no deben revelar descripciones, cuentas, hashes, claves ni
detalles de SQLite.

## Requisitos no funcionales

### RNF-01: Determinismo e integridad

Para el mismo conjunto de cartolas persistidas, parámetros y clasificaciones,
el análisis debe devolver el mismo resultado y orden. Los cálculos usan enteros
para montos y no dependen de red, reloj, IA ni estado externo.

### RNF-02: Resultados no persistidos

Una consulta de análisis no debe insertar, actualizar ni borrar filas de SQLite.
Eliminar una cartola debe eliminarla inmediatamente de análisis posteriores por
la lectura al vuelo.

### RNF-03: Compatibilidad y privacidad

La fase debe conservar el esquema SQLite v2 y los contratos actuales de
cartolas. Los resultados derivados están sujetos a la misma autenticación y
retención de los movimientos, y no deben ampliarse con datos sensibles que no
son necesarios para la métrica.

### RNF-04: Testabilidad

Las fórmulas, cobertura, compatibilidad de alcance, ordenamientos, recurrencias
y contrato HTTP deben probarse con movimientos sintéticos y SQLite temporal.

## Criterios de aceptación

- **CA-01:** Una consulta con cartolas compatibles calcula gasto, categorías,
  créditos y débitos excluidos según RF-02, sin usar saldos ni compensar
  créditos.
- **CA-02:** `sin_categoria` integra el gasto y su monto/cantidad se informa
  separadamente; la cobertura de comercios reconcilia con el gasto total.
- **CA-03:** Los límites `from` y `to` son inclusivos, los meses sin gasto se
  devuelven y la evolución cruza años correctamente.
- **CA-04:** Las variaciones mensuales informan diferencia absoluta y porcentaje
  redondeado; el primer mes, cobertura incompleta y período anterior cero usan
  los valores nulos definidos.
- **CA-05:** La cobertura informa rangos, huecos y meses parciales sin ocultar
  resultados parciales como completos.
- **CA-06:** Comercios principales agrupa por `merchant_key`, omite movimientos
  sin comercio y aplica el orden y límite definidos.
- **CA-07:** Los candidatos recurrentes cumplen el mínimo de tres ocurrencias y
  la cadencia semanal o mensual con sus tolerancias; secuencias irregulares no
  aparecen.
- **CA-08:** Cartolas faltantes, identificadores repetidos, parámetros de fecha
  inválidos, rango excesivo, moneda o cuenta incompatibles y períodos solapados
  se rechazan sin modificar SQLite.
- **CA-09:** `GET /v1/analysis` requiere autenticación, devuelve todas las
  secciones esperadas y una consulta válida vacía responde `200` sin datos
  sensibles.
- **CA-10:** El análisis no cambia el esquema ni persiste resultados; borrar una
  cartola modifica inmediatamente los análisis posteriores.

## Casos límite

- Rango de un solo día, límite inicial/final de mes y cruce de año.
- Mes sin movimientos, mes con cobertura parcial y hueco entre cartolas.
- Gasto anterior igual a cero.
- Movimientos de igual monto y fecha, pero comercios distintos.
- Empate de monto y cantidad entre comercios.
- Tres cobros alrededor del fin de mes, semanas desplazadas por fin de semana y
  una secuencia con un intervalo fuera de tolerancia.
- Crédito no categorizado, comisión y transferencia con una descripción que
  contiene un nombre personal.
- Cartolas con la misma cuenta visible, con cuentas totalmente enmascaradas y
  con períodos que solo se tocan en un día.
- Cartolas seleccionadas con diferentes versiones persistidas de ruleset.

## Supuestos

- Los períodos declarados por una cartola representan la cobertura disponible
  para sus movimientos.
- Las clasificaciones persistidas por la fase 6 son la fuente de verdad, aun si
  hay varias versiones de ruleset en el ámbito.
- La moneda `PESOS` de las cartolas de Cuenta Vista equivale a CLP entero sin
  unidades fraccionarias.
- Un `merchant_key` no nulo proviene de una regla determinista y es apto para
  agrupación interna autenticada.

## Preguntas abiertas

- ¿Qué contrato de identidad de cuenta se requerirá cuando el producto soporte
  varias cuentas sin una parte visible común?
- ¿Se necesitará permitir cartolas solapadas mediante una futura política de
  deduplicación con procedencia explícita?
- ¿Cuándo debe ampliarse el ruleset de comercios para aumentar la utilidad de
  rankings y recurrencias?

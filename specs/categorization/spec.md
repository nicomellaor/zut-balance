# Categorización determinista de movimientos

## Objetivo

Clasificar de forma determinista todos los movimientos persistidos, normalizar
comercios cuando una regla los identifica y conservar la trazabilidad del
resultado sin alterar la descripción original extraída de la cartola.

## Contexto

Las fases 1 a 5 entregan movimientos normalizados, validados y persistidos en
SQLite v1. La fase 6 habilita la capa previa a análisis mediante reglas
versionadas, sin IA, inferencia probabilística ni corrección manual.

## Alcance

- Migrar SQLite de esquema v1 a v2 sin perder cartolas ni movimientos.
- Clasificar movimientos existentes durante la migración y movimientos nuevos al
  persistir una cartola.
- Guardar una clasificación actual por movimiento en una tabla separada, con
  categoría, comercio opcional, regla y versión de ruleset.
- Aplicar reglas deterministas versionadas en código sobre una clave derivada de
  la descripción, sin modificar el texto original.
- Exponer la clasificación en las respuestas autenticadas de creación y consulta
  completa de cartolas.
- Mantener la eliminación en cascada de cartolas, movimientos y clasificaciones.

## Fuera de alcance

- IA, modelos estadísticos, scoring, confianza numérica o inferencias remotas.
- Corrección manual, usuarios, historial de cambios, overrides o administración
  HTTP de reglas.
- Reglas persistidas en SQLite, tablas maestras de comercios o categorías.
- Endpoints de listado o filtrado de movimientos.
- Reclasificación explícita de cartolas existentes después de cambiar reglas.
- Modificar descripciones, montos, fechas, tipo de movimiento o datos extraídos.

## Requisitos funcionales

### RF-01: Taxonomía fija

Cada movimiento debe tener exactamente una categoría de esta taxonomía plana:
`alimentacion`, `transporte`, `salud`, `entretenimiento`, `hogar`, `servicios`,
`compras`, `transferencias`, `comisiones`, `retiros`, `ingresos` o
`sin_categoria`.

### RF-02: Normalización de entrada y reglas

La clave de comparación debe derivarse de la descripción mediante mayúsculas,
eliminación de acentos, normalización de puntuación y espacios. La descripción
original debe preservarse literalmente.

Las reglas se definen en código con un identificador, versión y prioridad. Una
coincidencia exacta prevalece sobre una coincidencia de prefijo; entre reglas del
mismo tipo, gana la prioridad explícita. Si no hay regla aplicable, el resultado
es `sin_categoria` sin comercio ni `rule_id`.

### RF-03: Comercios y movimientos especiales

Una regla puede devolver `merchant_name` y `merchant_key` canónicos. Los
movimientos de transferencia, comisión o retiro deben clasificarse por sus
reglas específicas y pueden no tener comercio.

Los créditos también se clasifican. Un crédito no debe suponerse ingreso por su
signo: solo una regla puede asignar `ingresos`; en otro caso es
`sin_categoria`.

### RF-04: Persistencia y trazabilidad

SQLite v2 debe almacenar una sola clasificación por movimiento, asociada por FK
con borrado en cascada. Debe conservar `rule_id` opcional, `ruleset_version` y
`classified_at` para reproducir el resultado persistido.

La migración v1 a v2 debe clasificar todos los movimientos existentes en la
misma operación atómica. Una carga nueva debe guardar cartola, movimientos y
clasificaciones de forma atómica. La carga deduplicada debe reutilizar la
clasificación ya persistida.

### RF-05: Contrato HTTP

`POST /v1/statements` y `GET /v1/statements/{statement_id}` deben añadir a cada
movimiento una clasificación con `category`, `merchant_name`, `rule_id` y
`ruleset_version`. El listado de cartolas continúa sin movimientos ni
clasificaciones.

### RF-06: Reglas iniciales verificables

El ruleset inicial debe clasificar los patrones conocidos:

- `PAGO:CINEPLANET WEBPAY` como `entretenimiento` y comercio `Cineplanet`.
- `PAGO:SERVICIOS MEDICOS` como `salud` y comercio `Servicios Medicos`.
- Descripciones que comienzan por `TRASPASO A:` o `TRASPASO DE:` como
  `transferencias`, sin comercio.

## Requisitos no funcionales

### RNF-01: Determinismo

El mismo movimiento y la misma versión de reglas producen la misma
clasificación. El resultado no depende de red, fecha local, orden de ejecución
ni servicios externos.

### RNF-02: Privacidad

Comercios y claves derivadas son datos autenticados sujetos a la misma retención
y borrado que el movimiento. No deben exponer API keys, cuentas completas ni
contenido adicional del PDF en errores o logs.

### RNF-03: Compatibilidad e integridad

Una base v1 válida debe migrar sin pérdida de datos; una base v2 válida debe
reinicializarse sin cambios. Una base incompatible o de versión futura debe
fallar sin mutación. La respuesta mantiene todos los campos actuales de cada
movimiento y solo añade clasificación.

### RNF-04: Testabilidad

Las reglas, migración, cascade, idempotencia y respuestas API deben probarse con
datos sintéticos o anonimizados y bases SQLite temporales.

## Criterios de aceptación

- **CA-01:** Una base nueva se inicializa como v2 con las tres tablas y sus FK.
- **CA-02:** Una base v1 con cartolas y movimientos migra a v2 conservando cada
  fila y creando una clasificación por movimiento.
- **CA-03:** Una clasificación incluye categoría válida, versión de ruleset y
  `classified_at`; solo las coincidencias de regla incluyen `rule_id`.
- **CA-04:** Los patrones de RF-06 producen la categoría y comercio indicados,
  pese a variaciones de mayúsculas, acentos, puntuación o espacios.
- **CA-05:** Un movimiento sin regla queda `sin_categoria` y no inventa
  comercio, ingreso ni `rule_id`.
- **CA-06:** La descripción y campos normalizados originales no cambian durante
  la clasificación.
- **CA-07:** Una carga nueva persiste movimientos y clasificaciones de forma
  atómica; una carga idéntica reutiliza sus clasificaciones existentes.
- **CA-08:** `POST` y `GET` autenticados devuelven la clasificación de cada
  movimiento; `GET /v1/statements` continúa sin movimientos ni clasificaciones.
- **CA-09:** El borrado de una cartola elimina sus movimientos y clasificaciones.
- **CA-10:** Una base v2 incompleta o de versión futura se rechaza sin mutación.

## Casos límite

- Descripción vacía, solo puntuación o con múltiples espacios.
- Dos reglas con la misma prioridad y coincidencia para una descripción.
- Regla de prefijo y regla exacta aplicables al mismo movimiento.
- Crédito con descripción no reconocida.
- Movimiento histórico sin regla durante la migración.
- Error al clasificar un movimiento durante migración o guardado.
- Reintento de upload con los mismos bytes después de migrar a v2.
- Borrado repetido de una cartola con clasificaciones.

## Supuestos

- El ruleset inicial se distribuye con el código y se identifica como versión
  `1`.
- Una categoría puede ser `sin_categoria`; no se debe forzar cobertura mediante
  heurísticas.
- Las correcciones manuales se diseñarán en una fase posterior sin modificar el
  resultado de reglas ya persistido.

## Preguntas abiertas

- ¿Qué proceso de versionado y despliegue se usará cuando el ruleset cambie?
- ¿Cuándo se requerirá una operación explícita de reclasificación histórica?

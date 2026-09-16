# Plan técnico: análisis histórico

## Enfoque técnico

El endpoint de análisis cambiará de una lista manual de cartolas a una cartola
ancla. La API obtiene la cartola ancla, consulta en SQLite todas las cartolas con
el mismo banco, producto, moneda y número de cuenta con porción visible idéntica,
las ordena por período e identifica el rango efectivo. Las fechas `from` y `to`
son opcionales: sus ausencias se resuelven con los extremos del historial
compatible antes de invocar el dominio de análisis.

Una cuenta sin dígitos visibles no se puede agrupar con otras cartolas. Si se usa
como ancla, se analiza solamente esa cartola. Esta regla evita inventar identidad
de cuenta y no depende de saldos, movimientos ni heurísticas de frontera.

El dominio conservará períodos inclusivos para validar movimientos y cobertura,
pero distinguirá una frontera compartida de un solapamiento real. Dos períodos
son aceptables cuando el siguiente inicia el mismo día o después del final
anterior; solo se rechaza cuando inicia antes. Los movimientos de cada cartola se
agregan sin deduplicación semántica.

## Componentes

| Ruta | Cambio |
| --- | --- |
| `src/zut_balance/persistence.py` | Añadir una consulta de historial compatible desde una cartola almacenada, ordenada por período e identidad estable. |
| `src/zut_balance/analysis.py` | Eliminar límites de 100 cartolas/24 meses, aceptar fronteras compartidas y conservar rechazo de solapamientos reales. |
| `src/zut_balance/api.py` | Reemplazar `statement_id` por `anchor_statement_id`; resolver fechas opcionales y traducir errores del nuevo ámbito. |
| `tests/test_analysis.py` | Cubrir fronteras compartidas, solapamientos reales, huecos, rango amplio y cartolas sin identidad visible. |
| `tests/test_persistence.py` | Cubrir la consulta de historial por identidad visible, orden y exclusión de cuentas ocultas o incompatibles. |
| `tests/test_api.py` | Cubrir el contrato ancla, historial completo, fechas opcionales, errores y eliminación. |
| `README.md` y `docs/roadmap.md` | Actualizar el contrato HTTP y el estado de la fase tras completarla. |

## Modelo e interfaces

El modelo `AnalysisScope` se conserva para no ampliar la información sensible de
la respuesta. `statement_ids` pasa a representar el historial resuelto y siempre
se devuelve cronológicamente. `from_date` y `to_date` son el rango efectivo:

- sin filtros, mínimo `period_start` y máximo `period_end` de las cartolas
  incluidas;
- con un solo filtro, el extremo omitido se toma del historial resuelto;
- con ambos filtros, se usan exactamente esos límites tras validación.

Después de resolver el rango, la API conserva únicamente las cartolas cuyo
período declarado lo intersecta. Si no queda ninguna, responde `400` con un error
seguro de rango sin historial disponible.

La ruta `GET /v1/analysis` acepta:

```text
anchor_statement_id=<id>[&from=YYYY-MM-DD][&to=YYYY-MM-DD]
```

No acepta `statement_id` repetido ni selección manual. Las solicitudes del
contrato anterior pasan a ser inválidas, según la decisión aprobada de reemplazo.

La consulta del repositorio recibe la cartola ancla completa. Si su cuenta tiene
una porción visible, recupera los registros con la misma tupla
`(bank, product, currency, masked_account_number)` y los ordena por
`period_start`, `period_end`, `id`. Si no la tiene, devuelve solo el ancla.
SQLite v2 ya contiene esas columnas; no hace falta migración.

## Reglas de implementación

- Mantener el rechazo de bancos, productos y monedas incompatibles en el dominio
  como defensa de profundidad, aunque el repositorio ya filtre el historial.
- Reemplazar la comparación de solapamiento `current_start <= previous_end` por
  `current_start < previous_end`.
- Eliminar `MAX_STATEMENTS` y `MAX_MONTHS` junto con sus validaciones; no dejar
  límites duplicados en API, dominio o documentación.
- Resolver las fechas faltantes en la API con extremos de períodos persistidos,
  no con la primera o última fecha de movimientos.
- Si el rango solicitado no intersecta ningún período del historial, devolver un
  error seguro de rango sin historial disponible; no construir un ámbito con
  cartolas que no aportan cobertura.
- No usar saldo de apertura/cierre, descripción, monto, fecha o referencia para
  unir cuentas ni deduplicar movimientos.
- Mantener los errores seguros existentes: identificador ancla ausente o inválido
  devuelve `400`; ancla inexistente `404`; ámbito inválido `409`.

## Dependencias y migraciones

No se agregan dependencias ni se modifica el esquema SQLite v2. La ruta cambia
de forma incompatible al reemplazar los parámetros de solicitud; README y pruebas
deben reflejarlo en la misma entrega. El frontend queda fuera de esta fase y
necesitará una adaptación posterior antes de consumir el contrato nuevo.

## Estrategia de pruebas

1. Crear cartolas sintéticas de la misma cuenta con fronteras compartidas,
   períodos adyacentes, huecos y solapamientos reales.
2. Probar que la frontera compartida agrega movimientos de ambas cartolas una vez
   por procedencia y que un solapamiento real se rechaza.
3. Probar la consulta de repositorio con carga desordenada, varias cuentas,
   moneda/producto distintos y cuentas completamente enmascaradas.
4. Probar API con ancla, sin fechas, con una fecha, con ambas, más de 100
   cartolas y más de 24 meses.
5. Probar que la eliminación modifica inmediatamente el historial resuelto y la
   cobertura.
6. Ejecutar la suite Python completa. El frontend, E2E y Compose no cambian en
   esta fase porque todavía consumen el contrato anterior; su adaptación será una
   fase de interfaz posterior.

## Riesgos

- Cambiar el endpoint sin adaptar la SPA deja temporalmente el flujo web de
  análisis incompatible. Es un riesgo aceptado por el alcance backend-only y
  debe resolverse antes de desplegar la fase para usuarios de la UI.
- No deduplicar PDFs distintos puede contar dos veces un movimiento incluido por
  el banco en ambas cartolas de frontera. No existe una identidad de transacción
  suficiente para resolverlo sin falsos positivos; se conserva procedencia.
- Quitar límites permite consultas grandes. Deben medirse tiempos y memoria con
  fixtures de volumen antes de declarar la fase operativa.
- La política estricta de máscara oculta puede dejar cartolas fuera de una cadena
  histórica, pero evita mezclar cuentas sin identidad verificable.

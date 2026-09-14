# Plan técnico: categorización determinista de movimientos

## Enfoque técnico

Se añadirá un módulo puro de categorización que reciba la descripción y tipo de
un movimiento, produzca una clasificación inmutable y no acceda a SQLite ni
HTTP. Sus reglas versionadas vivirán en código y usarán coincidencias exactas y
de prefijo con prioridad explícita.

El repositorio SQLite incorporará migración v1 a v2. La migración validará v1,
creará `transaction_classifications`, clasificará los movimientos existentes y
actualizará `PRAGMA user_version` en una transacción. Las escrituras nuevas
insertarán movimientos y clasificaciones juntas; las lecturas unirán ambas para
reconstruir la respuesta enriquecida.

## Componentes

| Ubicación | Cambio |
| --- | --- |
| `src/zut_balance/categorization.py` | Crear taxonomía, normalización, reglas v1 y clasificador puro. |
| `src/zut_balance/models.py` | Añadir modelos inmutables de clasificación y movimiento enriquecido sin cambiar datos extraídos. |
| `src/zut_balance/persistence.py` | Migrar v1 a v2, persistir clasificaciones, validar v2 y reconstruir movimientos enriquecidos. |
| `src/zut_balance/api.py` | Serializar clasificación en POST y GET completo. |
| `tests/test_categorization.py` | Probar reglas, prioridad, normalización y fallback. |
| `tests/test_persistence.py` | Probar migración, atomicidad, cascade y deduplicación con clasificaciones. |
| `tests/test_api.py` | Probar contratos HTTP enriquecidos y privacidad. |
| `docs/database-schema.md` | Actualizar el esquema v2 de planificado a vigente tras Verify `PASS`. |
| `README.md` y `docs/roadmap.md` | Documentar categorías y marcar fase 6 completada solo después de Verify `PASS`. |

## Modelo e interfaces

- `Classification`: `category`, `merchant_name`, `merchant_key`, `rule_id`,
  `ruleset_version` y `classified_at`.
- El modelo de movimiento enriquecido conserva todos los campos de `Transaction`
  y adjunta una `Classification`; no altera `description`.
- `transaction_classifications.transaction_id` es PK y FK a `transactions.id`
  con `ON DELETE CASCADE`.
- El ruleset inicial se identifica como versión `1`; no se agrega tabla ni API
  de administración de reglas.

## Decisiones

- `SCHEMA_VERSION` sube de 1 a 2; no se aceptará un v1 sin migrarlo.
- Una categoría y clasificación existen para todo movimiento, incluido fallback.
- Créditos desconocidos quedan `sin_categoria`; el monto o tipo no infiere
  ingreso.
- Los resultados se materializan al migrar o crear la cartola. No se recalculan
  durante `GET` ni al reutilizar un upload deduplicado.
- El listado de cartolas no cambia para evitar cargar movimientos.
- No se añaden dependencias ni consultas de movimientos en esta fase.

## Estrategia de pruebas

- Casos unitarios de normalización, coincidencia exacta, prefijo, prioridad,
  transferencias y fallback.
- Migrar una base v1 real creada por el repositorio y comprobar conservación de
  datos y una clasificación por movimiento.
- Simular un fallo de clasificación/inserción y comprobar rollback de la
  migración o guardado.
- Verificar FK cascade desde cartola a movimiento y clasificación.
- Probar POST, GET, deduplicación y listado sin clasificaciones.
- Ejecutar la suite completa `pytest` y Verify contra CA-01 a CA-10.

## Riesgos y migración

- El esquema actual valida conjuntos exactos de columnas; v2 debe tener
  validadores separados para v1 y v2 durante la transición.
- La migración clasifica con ruleset v1 una sola vez. Cambios posteriores de
  reglas no cambian historial sin una fase explícita de reclasificación.
- Comercios derivados pueden ser sensibles; se almacenan solo bajo las rutas
  autenticadas actuales y se eliminan mediante cascade.

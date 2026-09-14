# Tareas: categorización determinista de movimientos

- [x] 1. Crear modelos y clasificador puro con taxonomía y ruleset v1.
  - Validación: pruebas unitarias cubren normalización, prioridad, Cineplanet, Servicios Medicos, transferencias y fallback.

- [x] 2. Implementar esquema v2 y migración atómica desde v1.
  - Validación: una base v1 válida conserva datos, crea una clasificación por movimiento y queda en `user_version = 2`.

- [x] 3. Persistir clasificaciones para nuevas cartolas y reconstruir movimientos enriquecidos.
  - Validación: guardado, consulta, deduplicación y cascade conservan exactamente una clasificación por movimiento.

- [x] 4. Exponer clasificación en POST y GET autenticados.
  - Validación: respuestas preservan campos existentes, añaden clasificación y listado sigue sin movimientos.

- [x] 5. Completar pruebas de rollback, privacidad, esquema incompatible y contratos HTTP.
  - Validación: pruebas cubren CA-01 a CA-10 con bases temporales y datos sintéticos.

- [x] 6. Actualizar documentación y verificar la entrega.
  - Validación: esquema v2 se marca vigente, README y roadmap se actualizan y `pytest` pasa.

# Tareas: análisis histórico

- [x] 1. Actualizar el dominio de análisis para fronteras compartidas y sin
  límites artificiales.
  - Validación: pruebas unitarias aceptan `period_end == period_start`, rechazan
    solo `period_end > period_start`, y cubren más de 100 cartolas y 24 meses.

- [x] 2. Añadir consulta de historial compatible desde una cartola ancla.
  - Validación: pruebas de repositorio verifican filtro por banco/producto/moneda
    y máscara visible exacta, orden cronológico y que una máscara oculta devuelve
    solo su ancla.

- [x] 3. Reemplazar el contrato HTTP de análisis por `anchor_statement_id` y
  fechas opcionales.
  - Validación: pruebas API cubren ancla inexistente, parámetro inválido, rango
    efectivo sin fechas, filtros parciales, rango sin historial y rechazo del
    contrato manual previo.

- [x] 4. Integrar resolución histórica, métricas y cobertura.
  - Validación: pruebas API con cartolas consecutivas, huecos y cruces de año
    verifican `scope.statement_ids`, totales, rangos cubiertos y meses parciales.

- [x] 5. Probar privacidad, efectos de eliminación y volumen sin límites.
  - Validación: pruebas confirman que no se exponen datos sensibles, la consulta
    no modifica SQLite y eliminar una cartola altera inmediatamente el historial.

- [x] 6. Actualizar documentación de API y verificar la fase.
  - Validación: README y roadmap reflejan el contrato ancla; `python -m pytest`
    pasa y la verificación contra `spec.md`, `plan.md` y estas tareas satisface
    CA-01 a CA-09.

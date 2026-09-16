# Tareas: señales estructuradas de análisis

- [ ] 1. Reemplazar el dominio narrativo por modelos y generador puro de señales.
  - Validación: pruebas de dominio cubren avisos, orden, determinismo, ausencia,
    highlight, variación nula y desempate por mes más reciente.

- [ ] 2. Reemplazar el contrato HTTP de `insights` por `notices` y `highlights`.
  - Validación: pruebas API exigen los campos nuevos, prohíben `insights` y
    verifican privacidad y ausencia de escritura SQLite.

- [ ] 3. Eliminar el código y pruebas obsoletos de insights narrativos.
  - Validación: no quedan importaciones, tipos, serialización ni pruebas de
    `insights`, `evidence`, `caveat` o prioridades narrativas.

- [ ] 4. Adaptar el cliente frontend al contrato anclado y a señales tipadas.
  - Validación: pruebas unitarias verifican `anchor_statement_id`, omisión de
    fechas vacías y tipos sin `Insight` ni selección manual de IDs.

- [ ] 5. Adaptar mínimamente la vista de análisis y dashboard.
  - Validación: pruebas de interfaz cubren una cartola ancla, avisos, highlight
    y la ausencia del feed `Hallazgos del período`, sin rediseñar el dashboard.

- [ ] 6. Actualizar E2E y ejecutar regresión completa.
  - Validación: E2E de escritorio y móvil pasa contra el contrato fase 10/11;
    Python, lint, pruebas/build frontend y smoke Compose pasan.

- [ ] 7. Actualizar documentación y verificar la fase.
  - Validación: README, roadmap y tareas reflejan el contrato final, y la
    verificación contra `spec.md`, `plan.md` y estas tareas satisface CA-01 a
    CA-09.

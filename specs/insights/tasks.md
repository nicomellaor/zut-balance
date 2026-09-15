# Tareas: insights deterministas

- [x] 1. Crear modelos y generador puro de insights a partir de `AnalysisResult`.
  - Validación: pruebas unitarias demuestran determinismo, evidencia no vacía,
    máximo de cinco y prioridades consecutivas.

- [x] 2. Implementar reglas de cobertura, calidad, resumen y variación mensual.
  - Validación: pruebas cubren huecos, meses parciales, clasificaciones mixtas,
    cero gasto, variaciones no disponibles y desempate por mes más reciente.

- [x] 3. Implementar reglas de categoría, comercio y recurrencia con lenguaje
  seguro.
  - Validación: pruebas cubren exclusión de `sin_categoria`, desempates, comercio
    ausente, candidato recurrente y ausencia de términos de suscripción o consejo.

- [x] 4. Exponer `insights` en `GET /v1/analysis` y actualizar su contrato.
  - Validación: pruebas API autenticadas verifican el campo aditivo, privacidad y
    que una consulta no modifica SQLite.

- [x] 5. Tipar el contrato y completar la presentación de métricas en la SPA.
  - Validación: pruebas de interfaz verifican cobertura, resumen, variaciones,
    comercios, recurrencias y estados vacíos sin recalcular datos.

- [x] 6. Añadir la sección accesible de insights con evidencia y advertencias.
  - Validación: pruebas de interfaz cubren insights normales, limitaciones,
    evidencia y `caveat`; teclado y alternativa textual siguen disponibles.

- [x] 7. Extender pruebas E2E y ejecutar la regresión completa.
  - Validación: E2E comprueba un flujo de análisis con insights en escritorio y
    móvil; Python, lint, unitarias, build, E2E y smoke Compose pasan.

- [x] 8. Actualizar documentación de estado y verificar criterios de aceptación.
  - Validación: README y roadmap reflejan el resultado implementado, y una
    verificación contra `spec.md`, `plan.md` y estas tareas confirma CA-01 a CA-10.

# Tareas: análisis determinista de gastos

- [x] 1. Crear modelos inmutables y validación pura del ámbito en `analysis.py`.
  - Validación: categorías incluidas/excluidas, moneda, cuenta, banco, producto,
    rango máximo e intersección inclusiva de períodos se validan con datos sintéticos.

- [x] 2. Implementar resumen de gasto, categorías y cobertura de comercios.
  - Validación: gasto, créditos, débitos excluidos, `sin_categoria` y cobertura
    de comercio reconcilian exactamente con los movimientos de entrada.

- [x] 3. Implementar cobertura temporal, meses calendario y variaciones.
  - Validación: límites inclusivos, meses vacíos, cruces de año, huecos, meses
    parciales, denominador cero y redondeo porcentual cumplen la especificación.

- [x] 4. Implementar comercios principales y candidatos recurrentes.
  - Validación: agrupación por `merchant_key`, desempates, top diez, cadencias,
    tolerancias, fin de mes e intervalos irregulares son deterministas.

- [x] 5. Añadir lectura completa de múltiples cartolas al repositorio.
  - Validación: las cartolas recuperadas conservan clasificaciones y un ID
    inexistente se identifica sin modificar SQLite.

- [x] 6. Exponer `GET /v1/analysis` autenticado con contrato seguro.
  - Validación: API valida parámetros e IDs, mapea errores acordados, devuelve
    todas las secciones y no expone descripciones ni otros campos sensibles.

- [x] 7. Completar pruebas integradas de alcance, borrado y no persistencia.
  - Validación: solapamientos o ámbitos ambiguos se rechazan, una consulta no
    cambia SQLite v2 y borrar una cartola afecta el análisis posterior.

- [x] 8. Actualizar documentación y verificar CA-01 a CA-10.
  - Validación: README y roadmap reflejan la entrega solo después de `pytest` y
    Verify `PASS` contra la especificación.

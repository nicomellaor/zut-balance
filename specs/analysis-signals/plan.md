# Plan técnico: señales estructuradas de análisis

## Enfoque técnico

La fase sustituye el módulo `insights` por un módulo de señales puro que recibe
exclusivamente `AnalysisResult`. El módulo devuelve dos estructuras tipadas:

- `notices`: cero, uno o dos avisos ordenados de cobertura incompleta y calidad
  de clasificación limitada.
- `highlights`: un contenedor con `largest_monthly_change` tipado o `null`.

La serialización de `GET /v1/analysis` elimina `insights` y expone ambas
estructuras. No cambia el cálculo de métricas ni el ámbito histórico resuelto en
la fase 10. No se mantienen el módulo, tipos, pruebas ni contrato anteriores de
insights.

Después de estabilizar y probar el backend, la SPA se adapta de forma mínima:
el cliente solicita análisis con una única cartola ancla y fechas opcionales,
el dashboard actual y usa componentes existentes para mostrar avisos y el
highlight; no rediseña jerarquía, tablas, gráficos ni móvil.

## Componentes

| Ruta | Cambio |
| --- | --- |
| `src/zut_balance/signals.py` | Crear dataclasses inmutables y generador puro de avisos y highlight. |
| `src/zut_balance/insights.py` | Eliminar el generador narrativo reemplazado. |
| `src/zut_balance/api.py` | Reemplazar la serialización de `insights` por `notices` y `highlights`. |
| `tests/test_signals.py` | Probar avisos, orden, ausencia, highlight, desempate, privacidad y determinismo. |
| `tests/test_insights.py` | Eliminar pruebas del contrato reemplazado. |
| `tests/test_api.py` | Actualizar contrato de análisis y probar respuesta sin `insights`. |
| `frontend/src/api.ts` | Reemplazar tipos `Insight` y método de análisis por señales y `anchor_statement_id`. |
| `frontend/src/App.tsx` | Reemplazar selección múltiple/feed narrativo por ancla, avisos y highlight mínimos. |
| `frontend/src/App.test.tsx` | Actualizar fixtures y probar contrato, ancla, avisos y highlight. |
| `frontend/e2e/dashboard.spec.ts` | Probar el flujo anclado y señales nuevas contra la API real. |
| `README.md`, `docs/roadmap.md` y `specs/analysis-signals/` | Actualizar contrato, estado y tareas tras la verificación. |

## Modelos e interfaces

El dominio tendrá modelos separados por tipo, sin etiquetas libres:

```text
CoverageNotice(kind, severity, gaps, partial_months)
ClassificationNotice(kind, severity, uncategorized_amount,
                     uncategorized_count, unidentified_merchant_amount,
                     unidentified_merchant_count, ruleset_versions)
LargestMonthlyChange(previous_month, current_month, previous_amount,
                     current_amount, absolute_change, percentage_change)
AnalysisSignals(notices, largest_monthly_change)
```

`notices` se serializa como una lista discriminada por `kind`; `highlights` se
serializa siempre como:

```json
{"largest_monthly_change": null}
```

o con el objeto tipado definido en la spec. No se envían títulos, cuerpos,
prioridades, `caveat` ni `evidence`.

En TypeScript se definen uniones discriminadas equivalentes. `api.getAnalysis`
acepta `anchorStatementId: string`, `from?: string` y `to?: string`, y solo
incluye parámetros de fecha cuando existan.

## Reglas de implementación

- Un aviso de cobertura copia rangos y meses de `AnalysisResult.coverage`; no
  vuelve a calcular cobertura.
- Un aviso de clasificación se genera si hay monto sin categoría, monto sin
  comercio identificado o múltiples versiones de ruleset; conserva todos los
  campos definidos, incluso valores cero.
- El highlight selecciona solo valores `absolute_change` distintos de `None` y
  de cero, con orden por valor absoluto descendente y mes descendente.
- La API llama una vez al generador y serializa cada unión explícitamente.
- La SPA usa la primera cartola elegida como ancla única. El usuario puede dejar
  fechas vacías para usar todo el historial; la UI no intenta resolver
  compatibilidad ni reconstruir el ámbito.
- Eliminar las funciones de etiquetas, formato de evidencia y feed de insights.
- La presentación mínima usa avisos compactos y un resumen factual de la mayor
  variación; no crea recomendaciones ni explicaciones causales.

## Dependencias y migraciones

No se agregan dependencias ni hay migración SQLite. El cambio HTTP es
incompatible y coincide con la adaptación de la SPA en esta misma fase. No se
publica compatibilidad temporal para `insights` ni para parámetros manuales de
análisis.

## Estrategia de pruebas

1. Probar el generador con `AnalysisResult` sintéticos para cobertura, calidad,
   cero gasto, reglas mixtas, variaciones positivas/negativas/nulas y empate.
2. Probar que los resultados son deterministas y no incluyen texto narrativo ni
   datos sensibles.
3. Actualizar pruebas HTTP para exigir `notices` y `highlights`, y prohibir
   `insights`.
4. Probar el cliente TypeScript para verificar que genera una consulta con
   `anchor_statement_id` y omite fechas vacías.
5. Probar la vista de análisis con una ancla, avisos y highlight; verificar que
   no queda feed narrativo ni selección múltiple.
6. Ejecutar E2E de escritorio y móvil contra la API de fase 10 y comprobar la
   solicitud anclada y el renderizado de señales.
7. Ejecutar Python, lint, pruebas/build frontend, E2E y smoke Compose antes de
   completar la fase.

## Riesgos

- El contrato cambia dos veces respecto de la SPA original: ancla de fase 10 y
  señales de fase 11. La adaptación mínima debe consumirse junto con ambos para
  que E2E represente el sistema real.
- La eliminación de `insights` rompe consumidores externos no identificados;
  está aprobada y debe documentarse en el README.
- Mantener el dashboard actual evita ampliar esta fase, pero sus problemas de
  repetición y responsive permanecen hasta el rediseño posterior.
- El aviso `limited_classification` puede mostrarse con valores muy bajos; la
  futura fase visual definirá su prioridad y densidad, no el backend.

# Plan técnico: insights deterministas

## Enfoque técnico

La fase añadirá una capa pura `insights` encima de `AnalysisResult`. Esta capa
recibirá el resultado completo de `analyze_statements`, construirá registros
inmutables de insight y no conocerá SQLite, FastAPI, sesión, PDF ni frontend.
La serialización HTTP añadirá los registros a la respuesta existente de
`GET /v1/analysis`; la SPA consumirá el contrato sin recalcular hechos.

El generador será determinista y basado en plantillas de texto en español. No se
introducirá IA, red, secretos, dependencias nuevas ni persistencia. La selección
se hará antes de serializar para asegurar el límite de cinco y las prioridades
consecutivas definidos en la especificación.

## Componentes

| Ruta | Cambio |
| --- | --- |
| `src/zut_balance/insights.py` | Crear modelos inmutables, reglas, plantillas y función pública que transforma `AnalysisResult` en insights. |
| `src/zut_balance/api.py` | Serializar `insights` como campo aditivo de la respuesta de análisis. |
| `tests/test_insights.py` | Crear resultados sintéticos y probar reglas, orden, desempates, evidencia y lenguaje seguro. |
| `tests/test_api.py` | Actualizar el contrato de análisis y comprobar autenticación, privacidad y no escritura con insights. |
| `frontend/src/api.ts` | Tipar el contrato estructurado de insights sin realizar cálculos financieros. |
| `frontend/src/App.tsx` | Completar la presentación de análisis existente y añadir tarjetas de insights con evidencia y advertencias. |
| `frontend/src/*.test.tsx` | Probar renderizado normal, vacío, advertencias y estados de insights. |
| `frontend/e2e/dashboard.spec.ts` | Comprobar en navegador métricas, limitaciones e insights observables. |
| `README.md` y `docs/roadmap.md` | Reflejar la fase final y los límites de OCR/IA si el resultado modifica la descripción pública. |

## Modelos e interfaces

El módulo de dominio definirá, como mínimo:

- `InsightKind`: enumeración de los siete `kind` del contrato.
- `InsightEvidence`: `label: str` y `value` serializable; los valores de monto
  quedan como enteros, fechas como ISO y meses como `YYYY-MM`.
- `Insight`: `kind`, `priority`, `title`, `body`, `evidence` y `caveat`.
- `generate_insights(result: AnalysisResult) -> tuple[Insight, ...]`.

Las funciones privadas construirán cada tipo candidato desde las secciones de
`AnalysisResult`. Una única función de selección aplicará el orden de RF-04,
el límite de cinco y asignará prioridades después de descartar candidatos. Esto
evita que cada regla deba conocer el límite global.

La API serializará los dataclasses de dominio explícitamente, del mismo modo que
las secciones actuales de análisis. El nuevo campo será siempre una lista y no
requerirá endpoint, parámetro o migración adicional.

## Reglas de implementación

- `coverage_warning` combinará huecos y meses parciales en un único registro.
- `data_quality_warning` reunirá las limitaciones presentes sin inventar un
  porcentaje; la evidencia contendrá los montos/cantidades y versiones que
  correspondan.
- `period_summary` será el único candidato obligatorio y mantendrá créditos y
  débitos excluidos como datos separados.
- La selección de `monthly_change` recorrerá únicamente cambios absolutos no
  nulos y aplicará valor absoluto descendente, mes descendente como desempate.
- `leading_category` excluirá `sin_categoria` y aplicará el orden canónico de
  categoría para desempates.
- `leading_merchant` usará el primer elemento ya ordenado de `top_merchants`.
- `recurrence_candidate` usará el primer elemento ya ordenado de
  `recurrence_candidates`, conservará fechas y usará lenguaje de candidato.
- Las plantillas no deben contener términos de causalidad, recomendación,
  predicción, consejo, salud financiera, ingreso ni suscripción confirmada.

## Presentación frontend

La vista `Dashboard` se separará en componentes pequeños de presentación para
evitar ampliar un único JSX monolítico. Recibirá exclusivamente `Analysis` y
renderizará:

- tarjetas de resumen, incluidos conteos, créditos y débitos excluidos;
- cobertura temporal y de clasificación/comercios;
- evolución y su tabla accesible, con variación absoluta y porcentual;
- categorías, comercios principales y recurrencias;
- sección de insights con orden de API, `title`, `body`, evidencia tabular o en
  lista y `caveat` visible.

La UI formateará montos y fechas, pero no derivará porcentajes, rankings,
prioridades ni texto financiero. Cada ausencia tendrá un mensaje específico en
lugar de una tarjeta vacía.

## Dependencias y migraciones

No se agregan dependencias Python o Node. No hay cambios a SQLite, Compose,
variables de entorno, autenticación, CORS ni backups. El campo HTTP aditivo puede
ser consumido por clientes existentes que ignoren claves desconocidas; las pruebas
del repositorio deberán dejar de exigir igualdad exacta del conjunto anterior de
claves y pasar a exigir el contrato completo vigente.

## Estrategia de pruebas

1. Probar el dominio con un constructor de `AnalysisResult` sintético para cada
   tipo, ausencia, orden, límite, desempate y repetición exacta.
2. Probar lenguaje prohibido y evidencia requerida, en especial cobertura,
   calidad, cambio mensual y recurrencia.
3. Probar API autenticada con `insights`, respuesta sin datos sensibles y que la
   consulta no modifica SQLite.
4. Probar el cliente y componentes React para insights normales, advertencias,
   vacío y campos opcionales.
5. Extender E2E para cargar fixture, calcular análisis y verificar tarjetas,
   tablas y mensajes de limitación en escritorio y móvil.
6. Ejecutar `python -m pytest`, lint, pruebas/build frontend y E2E; si Docker
   sigue siendo el mecanismo de despliegue, ejecutar el smoke test de Compose.

## Riesgos

- El ruleset actual identifica pocos comercios: la advertencia de calidad debe
  aparecer antes de cualquier afirmación de ranking que pueda malinterpretarse.
- La presentación de todas las métricas existentes amplía el trabajo de UI, pero
  es necesaria para cumplir la especificación de interfaz y hacer los insights
  auditables.
- Los textos son parte del contrato observable: cambios de redacción deberán
  actualizar pruebas de manera intencional.
- Una futura internacionalización requerirá reemplazar plantillas de dominio por
  claves de mensaje; queda fuera de esta fase en español único.

# Roadmap de Zut Balance

## Visión

Zut Balance busca convertir cartolas bancarias chilenas en información de gasto
confiable y útil. El producto avanza desde la extracción determinista de
documentos hacia categorización, análisis e insights. Cada capa depende de que
la anterior entregue datos normalizados, verificables y protegidos.

El flujo objetivo es:

```text
Cartola PDF -> ingesta y validación -> normalización -> categorización
-> análisis -> señales -> interfaz de usuario
```

La IA no debe interpretar documentos financieros sin procesar ni generar
conclusiones sobre datos no validados. Solo podrá asistir en etapas posteriores
sobre hechos calculados por componentes deterministas.

## Principios

- Priorizar exactitud, privacidad y resultados explícitos sobre extracciones parciales.
- Mantener separadas la ingesta, la clasificación, el análisis y la presentación.
- Usar reglas deterministas cuando resuelvan el problema de forma suficiente.
- Tratar cada formato bancario como un contrato independiente con pruebas reproducibles.
- Usar datos sintéticos o anonimizados y evitar conservar documentos originales innecesariamente.

## Estado actual

Las fases 1 a 11 y el despliegue privado están completados: existe una librería Python, un servicio HTTP
para la cartola digital de Cuenta Vista Banco de Chile. El parser valida el PDF,
reconoce el formato, normaliza sus movimientos, enmascara la cuenta y exige
conciliación general. La fase 2 añadió variantes sintéticas de varias páginas,
períodos que cruzan de año, columnas desplazadas y metadatos reordenados. La
fase 3 añadió carga HTTP validada. La fase 4 persiste datos normalizados en
SQLite, protegidos mediante API key y eliminables explícitamente, sin guardar
PDFs originales. La fase 6 clasifica movimientos con reglas deterministas. La
fase 7 calcula al vuelo métricas de gasto, variaciones, comercios y recurrencias
para cartolas seleccionadas. La fase 8 añade una SPA local para cargar cartolas,
revisar movimientos y explorar esas métricas. El despliegue privado añade Docker
Compose, TLS interno, sesión web y backups SQLite consistentes. No hay OCR ni IA.
La fase 9 añade insights estructurados, deterministas y trazables a la evidencia
del análisis, sin recomendaciones financieras ni servicios externos.
La fase 10 resuelve el análisis histórico desde una cartola ancla, incluyendo
cartolas compatibles de la misma cuenta visible y fronteras mensuales compartidas.
La fase 11 reemplaza los insights narrativos por avisos y highlights tipados, y
adapta la SPA al contrato anclado.

La fase 12 está completada: reemplaza la cartola ancla por un ámbito persistido
de cuenta y un catálogo autenticado. La fase 13 está completada: adapta la SPA a
ese contrato, automatiza la consulta y prioriza resumen y gráficos.

Las siguientes fases priorizan la operación privada confiable, documentación
clara para mantenimiento interno y una cobertura de categorización ampliable sin
perder determinismo ni privacidad.

Los requisitos y límites exactos están en
[`specs/banco-chile-cuenta-vista-ingestion/`](../specs/banco-chile-cuenta-vista-ingestion/)
y
[`specs/banco-chile-cuenta-vista-ingestion-hardening/`](../specs/banco-chile-cuenta-vista-ingestion-hardening/).

## Fases

| Fase | Resultado | Dependencia | Estado |
| --- | --- | --- | --- |
| 1. Ingesta inicial | Parser determinista de Cuenta Vista Banco de Chile, validado con fixture sintético y conciliación. | Ninguna. | Completada |
| 2. Robustecimiento de ingesta | Soporte aprobado para variantes sintéticas de layout, varias páginas y períodos que cruzan de año, respaldado por fixtures versionados. | Fase 1. | Completada |
| 3. Servicio de procesamiento | API de carga y consulta con límites, validación de entrada y controles de privacidad. | Fase 2. | Completada |
| 4. Persistencia | Modelo de datos para cartolas y movimientos normalizados, con política de retención de documentos. | Fase 3. | Completada |
| 5. Nuevos formatos | Primer incremento: layout v2 validado de Cuenta Vista Banco de Chile, con detección automática y pruebas reproducibles. | Fases 2 y 4. | Completada |
| 6. Categorización | Normalización de comercios y reglas deterministas de categorías, con corrección por usuario como mejora posterior. | Fase 4. | Completada |
| 7. Análisis | Métricas de gasto, variaciones, comercios principales y detección de recurrencias sobre datos categorizados. | Fase 6. | Completada |
| 8. Interfaz | Dashboard para cargar, revisar movimientos y explorar métricas. | Fases 3, 4 y 7. | Completada |
| 9. Insights deterministas | Explicaciones estructuradas sobre métricas y hechos calculados, con evidencia y salvaguardas contra conclusiones inventadas. | Fases 7 y 8. | Completada |
| 10. Análisis histórico | Ámbito por cuenta, fronteras mensuales compartidas y trazabilidad de cartolas incluidas. | Fase 7. | Completada |
| 11. Señales de análisis | Sustitución de insights narrativos por avisos y highlights tipados, con adaptación contractual mínima de SPA. | Fases 7 y 10. | Completada |
| 12. Análisis por cuenta | Identidad opaca de ámbito, catálogo de cuentas y reemplazo de `anchor_statement_id` por `account_id`. | Fases 4, 10 y 11. | Completada |
| 13. Flujo del dashboard | Selector compacto de cuenta, análisis automático y jerarquía centrada en resumen y gráficos. | Fases 8, 11 y 12. | Completada |
| 14. Documentación de proyecto privado | Reestructurar la documentación para uso y mantenimiento internos: propósito, capacidades y límites, arquitectura, inicio rápido, despliegue, privacidad y operación. | Fase 13. | Completada |
| 15. Operación local persistente | Configurar reinicio automático de `caddy` y `api` mediante Compose; el backup conserva ejecución manual. Documentar reinicio después de reboot, actualización, parada y persistencia de volúmenes. | Fase 14. | Completada |
| 16. TLS confiable en red privada | Documentar y verificar la exportación e instalación de la CA interna de Caddy en equipos autorizados, incluido Firefox cuando use un almacén propio. | Fase 15. | Completada |
| 17. Catálogo local de comercios y categorías | Sustituir reglas en código por un catálogo versionado dentro del repositorio, validado al iniciar y compatible con normalización, prioridad y trazabilidad actuales. Incluir reglas auditables para Cineplanet, Servicios Médicos, Unimarc, PedidosYa y otros comercios respaldados por pruebas. | Fase 6. | Planificada |
| 18. Administración local del catálogo | Evaluar reglas persistidas, alias, validación de conflictos y una interfaz o API administrativa para modificar el catálogo sin desplegar una nueva versión. | Fase 17. | Planificada |

## Orden de trabajo

Las fases 14 a 16 mejoran la operación y documentación sin alterar los contratos
financieros. La fase 15 solo aplica reinicio automático a servicios de larga
vida: el proceso de backup no debe reiniciarse ni programarse implícitamente.

La fase 16 conserva el modelo de TLS interno vigente. La advertencia de
certificado de Firefox ocurre cuando el navegador no confía en la CA interna de
Caddy; la solución es instalar esa CA en cada equipo autorizado, no ignorar la
advertencia ni desactivar HTTPS. Certificados públicos, DNS externo y exposición
a Internet continúan fuera de alcance.

La fase 17 mantiene las reglas deterministas, locales y versionadas, pero mueve
sus datos desde el código hacia un catálogo distribuido con el proyecto. Las
clasificaciones existentes no se recalculan automáticamente; en instalaciones de
prueba se pueden eliminar y volver a cargar cartolas. Un procesador como
`MERCADOPAGO` no se clasifica por defecto: solo se categoriza si la glosa permite
identificar confiablemente el comercio subyacente.

Cada fase pendiente comienza con una especificación en `specs/`, seguida por un
plan técnico, tareas pequeñas, implementación y verificación de criterios de
aceptación. Una fase no se considera completa solo porque sus pruebas pasen: se
debe comprobar que sus resultados observables satisfacen esos criterios.

## Iniciativas futuras no comprometidas

### Enriquecimiento externo de comercios

Un servicio remoto o catálogo externo de comercios podrá evaluarse después del
catálogo local de la fase 17. Antes de adoptarlo se debe definir el tratamiento
de privacidad de las glosas, licencias y cobertura para Chile, costos, caché,
disponibilidad, comportamiento ante fallos y criterios para no forzar categorías
sin evidencia suficiente. Será complementario al catálogo local y no sustituirá
el fallback `sin_categoria`.

OCR no forma parte del roadmap comprometido. Las cartolas escaneadas o sin texto
extraíble seguirán rechazándose de forma explícita, porque los formatos digitales
soportados se procesan directamente con validación estructural y conciliación.
Solo se evaluará OCR si aparecen muestras representativas y una necesidad real,
con precisión y límites de privacidad que puedan validarse antes de ampliar el
producto.

## Fuera del alcance inicial

No forman parte del roadmap inmediato Open Banking, modelos predictivos de
gasto o ahorro, asesoría financiera automática, chatbot financiero ni
presupuestos complejos. Se evaluarán únicamente cuando las fases de ingesta,
normalización y análisis hayan demostrado calidad suficiente.

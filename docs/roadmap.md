# Roadmap de Zut Balance

## Visión

Zut Balance busca convertir cartolas bancarias chilenas en información de gasto
confiable y útil. El producto avanza desde la extracción determinista de
documentos hacia categorización, análisis e insights. Cada capa depende de que
la anterior entregue datos normalizados, verificables y protegidos.

El flujo objetivo es:

```text
Cartola PDF -> ingesta y validación -> normalización -> categorización
-> análisis -> insights -> interfaz de usuario
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

Las fases 1 a 9 y el despliegue privado están completados: existe una librería Python, un servicio HTTP
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

## Orden de trabajo

La fase 9 cerró el alcance inicial con explicaciones estructuradas sobre hechos
calculados, sin introducir conclusiones financieras inventadas. No se incorporó
IA ni servicios externos: las reglas y textos son reproducibles y trazables a la
evidencia expuesta por el análisis.

Cada fase pendiente comienza con una especificación en `specs/`, seguida por un
plan técnico, tareas pequeñas, implementación y verificación de criterios de
aceptación. Una fase no se considera completa solo porque sus pruebas pasen: se
debe comprobar que sus resultados observables satisfacen esos criterios.

## Iniciativas futuras no comprometidas

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

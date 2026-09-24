# SDD compacto

Las features nuevas siguen `Specify -> Plan -> Implement -> Verify`. Este
proceso conserva decisiones verificables sin repetirlas en tres documentos.
Las specs existentes son históricas y no se reformatean salvo que una feature
activa requiera actualizar sus requisitos.

## Clasificación

Clasificar antes de crear artefactos. Ante duda, usar Estándar.

| Nivel | Cuándo usarlo | Artefactos |
| --- | --- | --- |
| Micro | Cambio local y reversible, sin contrato, persistencia, seguridad, privacidad ni arquitectura | Ninguno; implementar y validar directamente. |
| Estándar | Feature funcional o cambio coordinado habitual | `spec.md`, `plan.md` y `tasks.md` compactos. |
| Crítico | Migración, datos, seguridad, privacidad, API incompatible, despliegue riesgoso o cambio difícil de revertir | Los tres artefactos; ampliar solo los detalles que gestionen el riesgo. |

## Fuente única

Cada información tiene un único propietario:

| Información | Propietario |
| --- | --- |
| Comportamiento, límites y resultados observables | `spec.md` |
| Cambios técnicos, decisiones y riesgos | `plan.md` |
| Orden de ejecución, estado y comando de validación | `tasks.md` |
| Evidencia detallada | Pruebas, comandos ejecutados y reporte de verificación |

Usar IDs como `R1` y `R2` para referenciar requisitos. No copiar requisitos,
casos límite ni estrategias de prueba entre artefactos.

## Formato estándar

Para una feature Estándar, `spec.md` parte de:

```markdown
# <Feature>

## Resultado
<Resultado esperado en una o dos frases.>

## Límites
- Incluye: ...
- No incluye: ...

## Requisitos
| ID | Comportamiento observable | Casos relevantes |
| --- | --- | --- |
| R1 | ... | ... |

## Pendientes
<Solo preguntas que bloquean la planificación; omitir si no hay.>
```

`plan.md` documenta solo el delta técnico:

```markdown
# Plan: <Feature>

## Cambios
| Área | Cambio | Requisitos |
| --- | --- | --- |
| `src/...` | ... | R1 |

## Decisiones y riesgos
<Solo decisiones no obvias, compatibilidad, migración o rollback relevantes.>
```

`tasks.md` mantiene tareas verticales en orden de dependencia:

```markdown
- [ ] T1. Implementar ... (`R1`, `R2`). Verificar: `pytest tests/...`
```

Omitir toda sección sin contenido. Como guía para una feature Estándar, apuntar
a unas 100 líneas para `spec.md`, 80 para `plan.md` y 20 para `tasks.md`.
Estos límites no justifican omitir información necesaria.

## Detalles obligatorios cuando apliquen

Documentar explícitamente contratos observables y errores, compatibilidad,
invariantes, migración y rollback, seguridad, privacidad y preguntas
bloqueantes. En nivel Crítico, agregar estos detalles en el artefacto que les
corresponda, sin crear secciones ceremoniales ni duplicar contenido.

---
name: plan
description: Create compact technical plan.md and tasks.md for a Standard or Critical SDD feature without implementing code.
---

# Plan

Use this skill after a Standard or Critical feature specification is sufficiently
clear and before implementation.

1. Read repository instructions, `specs/README.md`, `specs/<feature>/spec.md`,
   and relevant code and documentation. If the specification is missing or has
   material open questions, stop and request clarification.
2. Create or update `specs/<feature>/plan.md` and `specs/<feature>/tasks.md` in
   the repository's predominant language, or the language requested by the user.
3. In `plan.md`, document only the technical delta: a `Área | Cambio |
   Requisitos` table, then non-obvious decisions and concrete risks. Reference
   requirement IDs; do not repeat their behavior, acceptance conditions, edge
   cases, or broad test strategy.
4. Include interfaces, dependencies, migrations, rollback, compatibility,
   security, and privacy only when the feature changes them. For Critical work,
   make the applicable invariants and recovery behavior explicit.
5. In `tasks.md`, create three to eight vertical implementation tasks in
   dependency order whenever practical. Each task is one checkbox with its
   requirement IDs and a specific validation command or check. Leave tasks
   unchecked until validation passes.
6. Keep the plan consistent with the specification. Do not silently alter
   requirements; surface conflicts, ambiguity, or necessary specification
   changes to the user.
7. Do not implement code or modify application behavior.

Finish by summarizing the technical decisions, task order, and unresolved risks.

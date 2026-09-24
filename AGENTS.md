# Agent Instructions

## Workflow

For Standard and Critical features:

1. Classify the change using `specs/README.md` before creating artifacts.
2. Read the relevant specification in `/specs`.
3. Do not implement before a technical plan exists.
4. Break the plan into small tasks.
5. Implement tasks incrementally.
6. Run tests after implementation.
7. Verify the result against acceptance criteria.
8. Update documentation when architecture changes.

Micro changes do not require persistent SDD artifacts. Implement and validate
them directly. When in doubt, classify the work as Standard.

## Engineering rules

- Prefer simple solutions.
- Do not introduce dependencies without justification.
- Preserve existing architecture unless the plan explicitly changes it.
- Add tests for business logic.
- Never silently change requirements.
- Ask for clarification when requirements are ambiguous.

## Spec-Driven Development (SDD)

Standard and Critical features follow: `Specify → Plan → Implement → Verify`.
Follow `specs/README.md` for classification, compact formats, and the
single-owner rule: requirements belong to `spec.md`, technical decisions to
`plan.md`, and execution state to `tasks.md`. Do not duplicate information
between these artifacts.

Use the corresponding skills in `.agents/skills/` and keep specifications,
plans, tasks, implementation, and verification aligned.

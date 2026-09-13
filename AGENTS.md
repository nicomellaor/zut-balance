# Agent Instructions

## Workflow

For non-trivial features:

1. Read the relevant specification in /specs.
2. Do not implement before a technical plan exists.
3. Break the plan into small tasks.
4. Implement tasks incrementally.
5. Run tests after implementation.
6. Verify the result against acceptance criteria.
7. Update documentation when architecture changes.

## Engineering rules

- Prefer simple solutions.
- Do not introduce dependencies without justification.
- Preserve existing architecture unless the plan explicitly changes it.
- Add tests for business logic.
- Never silently change requirements.
- Ask for clarification when requirements are ambiguous.

## Spec-Driven Development

Non-trivial features follow: `Specify → Plan → Implement → Verify`.

Use the corresponding skills in `.agents/skills/` and keep specifications, plans, tasks, implementation, and verification aligned.

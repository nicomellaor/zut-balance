---
name: plan
description: Read a feature specification and repository context to create specs/<feature>/plan.md and tasks.md without implementing code.
---

# Plan

Use this skill after a feature specification is sufficiently clear and before implementation.

1. Read repository instructions, `specs/<feature>/spec.md`, and relevant code and documentation. If the specification is missing or has material open questions, stop and request clarification.
2. Create or update `specs/<feature>/plan.md` and `specs/<feature>/tasks.md` in the repository's predominant language, or the language requested by the user.
3. In `plan.md`, document:
   - Technical approach
   - Components to create or modify
   - Relevant data models and interfaces
   - Dependencies and technical decisions
   - Test strategy
   - Risks and potential migrations
4. In `tasks.md`, create small implementation tasks in dependency order. Give every task a Markdown checkbox and an explicit validation criterion. Leave tasks unchecked until implementation validates them.
5. Keep the plan consistent with the specification. Do not silently alter requirements; surface conflicts, ambiguity, or necessary specification changes to the user.
6. Do not implement code or modify application behavior.

Finish by summarizing the technical decisions, task order, and unresolved risks.

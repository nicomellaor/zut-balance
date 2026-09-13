---
name: implement
description: Implement the next approved unchecked task from specs/<feature>/tasks.md, validating it against the feature specification and plan.
---

# Implement

Use this skill to execute approved work from a feature task list.

1. Read repository instructions and `specs/<feature>/spec.md`, `plan.md`, and `tasks.md`. Confirm that the task list is approved; if approval is not evident, ask the user before changing code.
2. Unless the user specifies another scope, select the next unchecked task in dependency order. Confirm its acceptance criteria and validation criterion before editing.
3. Implement only the selected task with small, coherent changes that follow the existing architecture and conventions. Preserve unrelated changes.
4. Run the tests, linters, builds, or other relevant checks defined by the repository or task validation criterion.
5. Mark the task complete in `tasks.md` only after its validation criterion passes. Record concise validation evidence when useful.
6. Stop and ask the user before proceeding if requirements are ambiguous, implementation would materially deviate from the plan, validation reveals a scope change, or a failure cannot be resolved without changing scope.
7. Do not modify `spec.md` to justify an implementation. Do not start a later task unless requested or the user asks to continue.

Finish by reporting the completed task, files changed, and validation results.

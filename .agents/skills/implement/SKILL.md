---
name: implement
description: Implement the next approved unchecked SDD task from specs/<feature>/tasks.md and validate it against its requirements and plan.
---

# Implement

Use this skill to execute approved work from a feature task list.

1. Read repository instructions, `specs/README.md`, and the feature's
   `spec.md`, `plan.md`, and `tasks.md`. Confirm that the task list is approved;
   if approval is not evident, ask the user before changing code.
2. Unless the user specifies another scope, select the next unchecked task in
   dependency order. Read only its referenced requirement IDs and relevant plan
   entries before editing.
3. Implement only the selected task with small, coherent changes that follow
   the existing architecture and conventions. Preserve unrelated changes.
4. Run the tests, linters, builds, or other relevant checks defined by the task
   validation criterion or repository instructions.
5. Mark the task complete in `tasks.md` only after its validation criterion
   passes. Keep detailed evidence in test output and the final report, not in
   the task list.
6. Stop and ask the user before proceeding if requirements are ambiguous,
   implementation would materially deviate from the plan, validation reveals a
   scope change, or a failure cannot be resolved without changing scope.
7. Do not modify `spec.md` to justify an implementation. Do not start a later
   task unless requested or the user asks to continue.

Finish by reporting the completed task, files changed, and validation results.

---
name: verify
description: Verify a Standard or Critical SDD feature against its requirements, plan, and tasks without modifying code.
---

# Verify

Use this skill to review completed or proposed feature work independently of implementation.

1. Read repository instructions, `specs/README.md`, and the feature's
   `spec.md`, `plan.md`, and `tasks.md`. Inspect the relevant implementation
   and its changes.
2. Run relevant tests, linters, builds, or targeted checks when available.
3. Evaluate every requirement ID individually. Compare the implementation with
   relevant plan entries and completed task validations; report plan deviations
   only when they exist.
4. Identify unmet requirements, confirmed defects, missing tests, architectural
   deviations, and unnecessary implementation.
5. Report findings ordered by severity, with concrete evidence such as file
   paths, line references, failing commands, or observed behavior. Clearly label
   each item as a confirmed failure or a potential risk.
6. Include a compact `Requisito | Estado | Evidencia` matrix. Do not repeat
   feature context, scope, or technical design.
7. Do not modify code, specifications, plans, tasks, or tests unless the user
   explicitly requests changes.
8. Conclude with exactly one verdict: `PASS`, `PASS WITH ISSUES`, or `FAIL`.

Finish with the verdict, requirement results, findings, and checks performed.

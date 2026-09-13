---
name: verify
description: Review a feature implementation against specs/<feature>/spec.md, plan.md, and tasks.md without modifying code.
---

# Verify

Use this skill to review completed or proposed feature work independently of implementation.

1. Read repository instructions and `specs/<feature>/spec.md`, `plan.md`, and `tasks.md`. Inspect the relevant implementation and its changes.
2. Run relevant tests, linters, builds, or targeted checks when available.
3. Evaluate every acceptance criterion individually and compare the implementation with the approved plan and completed task validations.
4. Identify unmet requirements, confirmed defects, missing tests, architectural deviations, and unnecessary implementation.
5. Report findings ordered by severity, with concrete evidence such as file paths, line references, failing commands, or observed behavior. Clearly label each item as a confirmed failure or a potential risk.
6. Do not modify code, specifications, plans, tasks, or tests unless the user explicitly requests changes.
7. Conclude with exactly one verdict: `PASS`, `PASS WITH ISSUES`, or `FAIL`.

Finish with the verdict, acceptance-criteria results, findings, and checks performed.

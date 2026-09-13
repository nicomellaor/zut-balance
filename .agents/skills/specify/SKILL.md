---
name: specify
description: Create or improve a feature specification at specs/<feature>/spec.md before technical planning or implementation.
---

# Specify

Use this skill when a feature needs a new or revised specification. Do not use it to plan architecture or implement code.

1. Read repository instructions and inspect relevant code, documentation, and existing specifications for context.
2. Identify the feature directory as `specs/<feature>/`. Use an existing feature directory when applicable; otherwise choose a concise lowercase, hyphenated feature name.
3. Create or improve `specs/<feature>/spec.md` in the repository's predominant language, or the language requested by the user.
4. Include these sections:
   - Goal
   - Context
   - Scope
   - Out of scope
   - Functional requirements
   - Non-functional requirements
   - Verifiable acceptance criteria
   - Edge cases
   - Assumptions
   - Open questions
5. Make requirements testable and acceptance criteria observable. Preserve confirmed requirements and clearly distinguish facts from assumptions.
6. Do not decide the technical architecture, implement code, create planning documents, or invent requirements. When an important ambiguity prevents a sound specification, record it as an open question and ask the user for clarification.

Finish by summarizing the specification and any unresolved questions.

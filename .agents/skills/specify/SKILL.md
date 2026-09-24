---
name: specify
description: Classify a change and create a compact SDD specification at specs/<feature>/spec.md when it is Standard or Critical.
---

# Specify

Use this skill when a feature needs a new or revised specification. Do not use
it to plan architecture or implement code.

1. Read repository instructions, `specs/README.md`, and inspect relevant code,
   documentation, and existing specifications for context.
2. Classify the work as Micro, Standard, or Critical. For Micro work, report
   that no persistent SDD artifacts are needed and stop. When uncertain, use
   Standard.
3. Identify the feature directory as `specs/<feature>/`. Use an existing
   feature directory when applicable; otherwise choose a concise lowercase,
   hyphenated feature name.
4. Create or improve `specs/<feature>/spec.md` in the repository's predominant
   language, or the language requested by the user. Use `Resultado`, `Límites`,
   and a requirements table with stable IDs such as `R1`. Include `Pendientes`
   only for questions that block planning.
5. Make every requirement observable. Put its acceptance condition and relevant
   edge cases in its table row instead of duplicating separate sections. Include
   non-functional requirements only when they are specific to the feature.
6. For Critical work, add only the required details for contracts, errors,
   compatibility, invariants, migration, rollback, security, or privacy.
7. Do not decide technical architecture, implementation tasks, or detailed test
   strategy. Do not invent requirements or add empty sections. When an
   important ambiguity prevents a sound specification, record it as a pending
   question and ask the user for clarification.

Finish by summarizing the specification and any unresolved questions.

---
paths:
  - "skills/**"
---

# Skill Authoring Rules

**Trigger**: Creating / modifying `skills/**/SKILL.md`.

## P0.5 · Skill Body Must Not Contain Project-Specific Identifiers

Forbidden to hardcode project-specific class names / URLs / DOM class names / business terms; must abstract to generic placeholders; project-level details go in `rules/` or `docs/`.

❌ Writing in a skill: "<role> endpoint `/<specific route>/*` has no `.<specific class name>`"
✅ Skill writes: "Does the test case navigation target leave the portal layout?"

## P0.6 · Scope Limited to the Project's Actual Tech Stack

Only write about stacks actually used in the project (Playwright + pytest); do not generalize to unverified combinations.

❌ `description: ... applicable to Playwright / Selenium / Cypress ...`
✅ `description: Playwright + pytest ...`

## P0.7 · New Skills Must Complete Four Required Companions

1. Register in CLAUDE.md route table
2. Add cross-references in related skills
3. Self-check and remove project-specific identifiers
4. When new project facts are produced, sync update `docs/`

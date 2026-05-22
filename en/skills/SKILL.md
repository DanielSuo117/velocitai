---
name: ui-automation-harness
description: UI regression test sub-skill router entry point.
---

# UI Regression Testing — Main Skill

## Composite Scenarios

- Add new page and run it → `gen-page-test` → `test-runner`
- Replace locators and verify → `locator-replacer` → `test-runner`
- Add features to an existing page → `add-regression-point` → `test-runner`
- Navigation test cases that leave the portal layout → `add-regression-point` + `case-round-trip` → `test-runner`
- Design load assertion for a new page → `page-load-assertion` → `gen-page-test`
- Review changes → `code-review-graph` → `test-runner`
- Locate a bug → `code-review-graph` (debug workflow)
- Safe refactoring → `code-review-graph` (refactor workflow)
- Fix failing tests → `test-runner` (detect failure) → `quick-debug` (login-free triage + auto-fix) → `test-runner` (regression verification)
- Verify after form save → `save-verify-strategy` (choose verification method) → `test-runner` (run verification)

## Reference Index

Coding conventions, project facts, and behavior rules are all guided by [CLAUDE.md](../CLAUDE.md) and not repeated here.

Key references:
- Naming + base classes + test organization → [coding-conventions/](../rules/coding-conventions/)
- Locator restrictions + wait strategy + context sharing → [playwright/](../rules/playwright/)
- Agent behavior boundaries → [agent-behavior/](../rules/agent-behavior/)

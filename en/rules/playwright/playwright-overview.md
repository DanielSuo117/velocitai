---
paths: []
---

# Playwright Usage Rules

> This file is a navigation index (`paths: []` — not auto-loaded); sub-rule files each declare their own paths and are loaded on demand. Access via CLAUDE.md route table or rules-index.md when needed.

---

## Sub-Rule Index

| Topic | File | Keywords |
|------|------|--------|
| Timeout triage & wait strategy | [timeout-and-wait.md](./timeout-and-wait.md) | TimeoutError, page.url, new tab, networkidle, SPA rendering |
| Locator strategy | [locator-strategy.md](./locator-strategy.md) | Forbidden items, ARIA role, chained `>>`, exact match |
| New tab detection | [new-tab-detection.md](./new-tab-detection.md) | expect_page, window.open, target="_blank" |
| Browser context | [browser-context.md](./browser-context.md) | context sharing, cross-domain isolation, class-level |
| Assertion patterns | [assertion-patterns.md](./assertion-patterns.md) | Toast, UI state change, wait target uniqueness |
| Third-party components | [third-party-components.md](./third-party-components.md) | Arco Design, dropdown close |
| Performance API isolation | [performance-api-isolation.md](./performance-api-isolation.md) | clearResourceTimings, cross-test contamination, batch failure |

## Cross-References

- Complete six-level locator priority → [locator-replacer skill](../../skills/locator-replacer/SKILL.md)
- Detailed wait strategy methodology → [wait-strategy skill](../../skills/wait-strategy/SKILL.md)
- Agent browser tool selection → [agent-behavior](../agent-behavior/agent-behavior.md) P0.4

# UI Regression Testing — Project Map

> Python + Playwright + pytest POM regression framework. This file is the agent's sole entry-point index.

---

## Behavior Boundaries (Read Before Starting)

Must confirm `--env` before running tests; Git operations require user authorization; ask when docs conflict with code.

Full terms → [agent-behavior.md](./rules/agent-behavior/agent-behavior.md)

---

## Route Table

| What to do | Where to go |
|---------|--------|
| **Create** page object + tests | [gen-page-test](./skills/gen-page-test/) |
| **Add** regression points to existing page | [add-regression-point](./skills/add-regression-point/) |
| **Replace** locators / analyze DOM | [locator-replacer](./skills/locator-replacer/) |
| **Run** tests / analyze results | [test-runner](./skills/test-runner/) |
| **Debug** test failures | [quick-debug](./skills/quick-debug/) |
| Design **is_page_loaded** | [page-load-assertion](./skills/page-load-assertion/) |
| Configure **wait strategy** | [wait-strategy](./skills/wait-strategy/) |
| Configure **browser** viewport/timeout | [browser-config](./skills/browser-config/) |
| Test case **round-trip closure** | [case-round-trip](./skills/case-round-trip/) |
| **Save verification** strategy | [save-verify-strategy](./skills/save-verify-strategy/) |
| **Architecture** decisions / layering / new roles | [architecture](./skills/architecture/) |
| **Code review** / exploration / refactoring | [code-review-graph](./skills/code-review-graph/) |
| Composite scenarios (multi-skill chains) | [SKILL.md](./skills/SKILL.md) |
| **Coding conventions** (naming/base classes/test cases) | [coding-conventions](./rules/coding-conventions/coding-conventions.md) |
| **Playwright rules** index | [playwright-overview](./rules/playwright/playwright-overview.md) |
| **Performance API isolation** | [performance-api-isolation](./rules/playwright/performance-api-isolation.md) |
| **Test report generation strategy** | [report-strategy](./rules/report-strategy/report-strategy.md) |
| PageObject catalog | [docs/pages-catalog.md](./docs/pages-catalog.md) |
| Regression test points | [docs/regression-points.md](./docs/regression-points.md) |
| Project architecture | [docs/architecture.md](./docs/architecture.md) |
| Environment setup | [docs/setup.md](./docs/setup.md) |

---

## Self-Evolution Mechanism (P0 Highest Priority)

**Trigger**: Before task completion / after encountering pitfalls / after user corrections / on recurrence of similar issues.

| Type | Persistence Target |
|------|---------|
| Experience (How-to) | Corresponding `skills/` SKILL.md |
| Rules (Must/Must-not) | `rules/<topic>/` corresponding sub-file (must include ❌ anti-pattern + ✅ best practice) |
| Project facts (class names/URLs/catalogs) | Corresponding `docs/` file |

Execution: Edit with minimal incremental writes; declare at end of reply `📝 Persisted to <file>: <summary>`.

---

## Commands

```bash
source .venv/bin/activate

# Run by module (--env must be specified by user)
pytest tests/<role>/test_<role>_flow.py --env=<pre|prod>

# Full regression
pytest tests/ --env=<pre|prod>

# Report
allure serve reports/allure-results
```

Private notes: [CLAUDE.local.md](./CLAUDE.local.md) (not committed).

---

## Tools & Agents

- **code-review-graph MCP**: When exploring the codebase, prefer the graph tool first, then fall back to Grep/Glob/Read. Workflow methodology → [code-review-graph skill](./skills/code-review-graph/)
- **code-reviewer agent**: Code review and defect verification → [code-reviewer.md](./.claude/agents/code-reviewer.md)

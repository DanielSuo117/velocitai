# Agent Behavior Rules

Applies to: the agent's own decision-making process (across all skills / rules / code)

---

## 🚦 Boundary Quick Reference

### Behavior Boundaries

| Category | Allowed | Must Ask First | Forbidden |
|------|------|-----------|------|
| Code changes | Edit `pages/` / `tests/` / `config/` / `conftest.py` | —— | —— |
| Running tests | —— | Environment (`--env=pre` / `--env=prod`), scope | Defaulting `--env=prod` on own |
| Doc/code conflict | —— | Explain the conflict + two options to user, let user decide | Self-deciding, silent correction |
| Git | Read-only + `git add` (stage only) | `commit` / `push` only with explicit authorization | Auto `commit` / `push` / `--amend` / `--force` |

Project facts quick reference (architecture / PageObject / regression points / environment setup) → [CLAUDE.md route table](../../CLAUDE.md)

---

## 🔴 P0.1 · Must Ask When Docs and Code Are Inconsistent

**Trigger**: Discovers conflict between `docs/` / `skills/` / `rules/` content and source code.

**Rule**: Forbidden to self-decide or silently correct; must explain the conflict + two options to the user, and only act after user decides.

❌ Anti-pattern: Discovers skill example uses `--env=pre` while `DEFAULT_ENV="prod"`, directly copies from skill or quietly changes one side.

✅ Best practice: Report to user: "skill example uses `pre`, code defaults to `prod` — please confirm which side is correct".

---

## 🔴 P0.2 · Must Confirm `--env` Before Running Tests

**Trigger**: User requests running tests but has not specified `--env=pre` or `--env=prod`.

**Rule**: Forbidden to default to any environment; must ask for environment and scope first, then execute.

❌ Anti-pattern:

```
User: run the test cases
agent: pytest tests/<role>/test_<role>_flow.py --env=prod -v   # defaulted to prod on own
```

✅ Best practice:

```
User: run the test cases
agent: Please confirm the environment: --env=pre or --env=prod? Scope: full regression or -k <case>?
```

---

## 🔴 P0.3 · Git Commits and Pushes Are Executed by User Only

**Trigger**: Code/doc changes are complete and ready to be committed.

**Rule**: Forbidden to `git commit` / `git push` (including `--amend` / `--force`). After changes are done, list a summary + suggest a commit message, and prompt the user to execute manually. Exception when user explicitly authorizes; authorization only applies to the current instance.

❌ Anti-pattern: After writing code, automatically run `git add && git commit -m "feat: ..."`.

✅ Best practice:

```
✅ Completed:
- Added pages/xxx.py (new PageObject)
- Modified tests/xxx.py (added test cases)
Suggested commit message: feat(pages): add XX page object + corresponding test cases
Please execute manually: git add pages/xxx.py tests/xxx.py && git commit
```

---

## 🔴 P0.4 · Browser Tool Selection: agent-browser for Capture / Playwright MCP for Verification

**Trigger**: When browser interaction is needed.

**Rule**: Use `agent-browser` for DOM exploration / locator collection (~200–400 tokens/call); use Playwright MCP for regression verification / assertion checking; if `agent-browser` is not installed, fall back to Playwright MCP for everything.

P0.4.1–P0.4.4 detailed anti-patterns/best practices → [browser-tool-usage.md](./browser-tool-usage.md).

---

P0.5–P0.7 (Skill authoring rules) → only loaded when editing `skills/**` → [skill-authoring.md](./skill-authoring.md)

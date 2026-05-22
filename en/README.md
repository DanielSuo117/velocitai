# VelocitAI

**A complete UI automation methodology for your coding agents, built on composable skills and enforced rules.**

VelocitAI is an agent harness — not another test framework — that gives AI agents the ability to **autonomously generate, execute, debug, and evolve** enterprise-grade UI test code using Python + Playwright + pytest.

> 15 working days with AI Agent vs. 60 working days manual coding — **4x development speed**.

---

## Installation

### Claude Code (recommended)

```bash
claude install-plugin velocitai
```

### Copilot CLI

```bash
# Clone and copy to your project
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{skills,rules,hooks,docs,CLAUDE.md,AGENTS.md} your-project/
```

### Gemini CLI

```bash
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{skills,rules,hooks,docs,CLAUDE.md,GEMINI.md} your-project/
```

### Manual Setup

```bash
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{.claude,.claude-plugin,skills,rules,hooks,docs,CLAUDE.md,AGENTS.md,GEMINI.md} your-project/
```

---

## What's Inside

### 13 Skills (How-to)

Skills teach your agent _how_ to do things — step-by-step operational guides.

| Skill | Purpose |
|-------|---------|
| `ui-automation-harness` | Router: composes sub-skills into multi-step workflows |
| `gen-page-test` | Generate PageObject + test file from a target page |
| `add-regression-point` | Add regression test points to existing pages |
| `locator-replacer` | Replace fragile locators using 6-level priority (P0 ARIA → P5 XPath) |
| `test-runner` | Run tests + structured failure analysis |
| `quick-debug` | 3-step timeout triage: page → tab → locator |
| `page-load-assertion` | Design `is_page_loaded()` with 4 verification modes |
| `wait-strategy` | Configure implicit/explicit wait strategies |
| `browser-config` | Viewport, timeout, context, headless/headed |
| `case-round-trip` | Ensure test round-trip closure (state consistency) |
| `save-verify-strategy` | Toast / redirect / data comparison / rich-text verification |
| `architecture` | Architecture decisions, inheritance design, role splitting |
| `code-review-graph` | AST knowledge graph driven code review |

### 14 Rule Files (Must / Must-not)

Rules enforce hard constraints. Every rule includes ❌ anti-pattern + ✅ best practice.

| Domain | Files | Key Rules |
|--------|-------|-----------|
| **Agent Behavior** | 3 | Confirm `--env` before tests; no auto-commit; ask on doc/code conflict |
| **Coding Conventions** | 1 | PascalCase classes, snake_case methods, locator class constants |
| **Playwright** | 8 | 6-level locator priority, no `time.sleep()`, context isolation |
| **Report Strategy** | 1 | HTML report only on failure, auto-rotation, domain stats |

### 1 Sub-Agent

- **code-reviewer**: P0/P1/P2 graded review + AST impact radius analysis

### Self-Evolution

VelocitAI agents learn from mistakes. After encountering issues, they automatically persist learnings:

| Type | Target |
|------|--------|
| How-to (experience) | `skills/<topic>/SKILL.md` |
| Must/Must-not (rule) | `rules/<domain>/<rule>.md` |
| Project facts | `docs/<file>.md` |

---

## Workflow

```
1. Explore page       → agent-browser (82-93% token savings vs Playwright MCP)
2. Generate PageObject → gen-page-test skill
3. Write test cases    → add-regression-point + case-round-trip
4. Run & debug         → test-runner → quick-debug (auto 3-step triage)
5. Code review         → code-reviewer agent + AST knowledge graph
6. Evolve              → auto-persist to skills / rules / docs
```

---

## Project Structure

```
velocitai/
├── CLAUDE.md                 # Agent entry point & route table
├── AGENTS.md                 # Copilot CLI entry point
├── GEMINI.md                 # Gemini CLI entry point
├── package.json              # npm distribution
├── .claude-plugin/           # Claude Code plugin config
│   ├── plugin.json
│   └── marketplace.json
├── .claude/                  # Claude-specific config
│   ├── settings.json         # Permissions + hooks
│   └── agents/               # Sub-agent definitions
│       └── code-reviewer.md
├── skills/                   # Operational skills (How-to)
│   ├── SKILL.md              # Router (composes sub-skills)
│   ├── gen-page-test/
│   ├── locator-replacer/
│   ├── test-runner/
│   ├── quick-debug/
│   └── ... (13 total)
├── rules/                    # Enforced rules (Must/Must-not)
│   ├── agent-behavior/       # 3 files
│   ├── coding-conventions/   # 1 file
│   ├── playwright/           # 8 files
│   └── report-strategy/      # 1 file
├── hooks/                    # Session & tool hooks
│   └── hooks.json
└── docs/                     # Project knowledge base
    ├── architecture.md
    ├── pages-catalog.md
    ├── regression-points.md
    └── setup.md
```

---

## Compatible Agents

| Platform | Status | Entry File |
|----------|--------|------------|
| **Claude Code** | Native support (plugin) | `CLAUDE.md` |
| **GitHub Copilot CLI** | Skills compatible | `AGENTS.md` |
| **Gemini CLI** | Skills compatible | `GEMINI.md` |
| **Cursor** | Rules compatible | `CLAUDE.md` |
| **Windsurf** | Rules compatible | `CLAUDE.md` |

---

## Tech Stack

- **Python 3.10+** — Core language
- **Playwright** — Browser automation
- **pytest** — Test framework
- **Allure** — Test reporting
- **agent-browser** — AI browser DOM exploration (optional, Rust CLI)
- **code-review-graph** — AST knowledge graph MCP (optional)

---

## Quick Start

```bash
# 1. Clone and integrate
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{skills,rules,hooks,docs,.claude,CLAUDE.md} your-project/

# 2. Install dependencies
cd your-project
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 3. Run tests (--env is REQUIRED)
pytest tests/ --env=pre

# 4. View report
allure serve reports/allure-results
```

---

## License

MIT

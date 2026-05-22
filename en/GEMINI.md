# VelocitAI — Gemini CLI Instructions

> This file is the entry point for Gemini CLI agents.

## What is this?

VelocitAI is a UI automation agent harness for Python + Playwright + pytest POM projects.
It provides skills (how-to), rules (must/must-not), and a self-evolution mechanism.

## Skill & Rule System

- **Skills** are in `skills/` — each subfolder contains a `SKILL.md` with step-by-step instructions.
- **Rules** are in `rules/` — enforced constraints with anti-patterns and best practices.
- The router skill is `skills/SKILL.md` — it composes multiple sub-skills.

## Key Constraints

1. Never run tests without confirming `--env=pre` or `--env=prod` with the user.
2. Never auto-commit or auto-push. List changes and suggest commit message; let the user execute.
3. When docs conflict with code, ask the user which side is correct.

## Route Table

See [CLAUDE.md](./CLAUDE.md) for the full routing table mapping tasks to skills.

## Tool Mapping

| Claude Code Tool | Gemini CLI Equivalent |
|-----------------|---------------------|
| Skill           | activate_skill      |
| Read            | read_file           |
| Edit            | edit_file           |
| Write           | write_file          |
| Bash            | run_command         |
| Grep            | search              |
| Glob            | glob                |

## Self-Evolution

After completing tasks or encountering issues, persist learnings:
- How-to → `skills/<topic>/SKILL.md`
- Must/Must-not → `rules/<domain>/<rule>.md`
- Project facts → `docs/<file>.md`

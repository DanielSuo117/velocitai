# VelocitAI — Agent 使用说明

> 本文件是 GitHub Copilot CLI 及其他读取 AGENTS.md 的代理的入口文件。

## 这是什么？

VelocitAI 是一套针对 Python + Playwright + pytest POM 项目的 UI 自动化代理治理框架（Agent Harness）。
它提供技能（how-to 操作指南）、规则（must/must-not 强制约束）和自我进化机制。

## 技能与规则体系

- **技能**位于 `skills/` 目录 —— 每个子目录包含一个 `SKILL.md`，提供分步操作说明。
- **规则**位于 `rules/` 目录 —— 包含反模式和最佳实践的强制约束。
- 路由技能为 `skills/SKILL.md` —— 负责编排多个子技能。

## 核心约束

1. 运行测试前必须向用户确认 `--env=pre` 或 `--env=prod`，不得自行默认。
2. 禁止自动提交或自动推送。列出变更并建议 commit message，由用户执行。
3. 文档与代码冲突时，询问用户哪一方正确。

## 路由表

完整的任务到技能的路由映射，请参见 [CLAUDE.md](./CLAUDE.md)。

## 工具映射

| Claude Code 工具 | Copilot CLI 对应工具 |
|-----------------|---------------------|
| Skill           | skill               |
| Read            | read_file           |
| Edit            | edit_file           |
| Write           | write_file          |
| Bash            | run_command         |
| Grep            | search              |
| Glob            | glob                |

## 自我进化机制

完成任务或遇到问题后，将经验持久化：
- How-to（操作经验）→ `skills/<主题>/SKILL.md`
- Must/Must-not（约束规则）→ `rules/<规则域>/<规则>.md`
- 项目事实 → `docs/<文件>.md`

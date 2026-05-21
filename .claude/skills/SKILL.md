---
name: ui-automation-harness
description: UI 回归测试子 skill 路由入口。
---

# UI 回归测试 — 主 Skill

## 组合场景

- 新增页面并跑通 → `gen-page-test` → `test-runner`
- 替换定位符并验证 → `locator-replacer` → `test-runner`
- 给已有页面加功能 → `add-regression-point` → `test-runner`
- 脱离门户布局的跳转用例 → `add-regression-point` + `case-round-trip` → `test-runner`
- 设计新页面的加载验证 → `page-load-assertion` → `gen-page-test`
- 审查变更 → `code-review-graph` → `test-runner`
- 定位 bug → `code-review-graph`（调试工作流）
- 安全重构 → `code-review-graph`（重构工作流）
- 测试失败纠错 → `test-runner`（发现失败）→ `quick-debug`（免登排查 + 自动修复）→ `test-runner`（回归验证）
- 表单保存后验证 → `save-verify-strategy`（选择验证方式）→ `test-runner`（运行验证）

## 引用索引

编码规范、项目事实、行为规则等均由 [CLAUDE.md](../../CLAUDE.md) 统一指引，此处不重复。

关键引用：
- 命名 + 基类 + 用例组织 → [coding-conventions/](../rules/coding-conventions/)
- 定位符禁令 + 等待策略 + context 共享 → [playwright/](../rules/playwright/)
- Agent 行为边界 → [agent-behavior/](../rules/agent-behavior/)

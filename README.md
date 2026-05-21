# VelocitAI — UI Automation Harness

> Next-generation UI automation harness powered by Python & Playwright. Chat with AI Agents to seamlessly generate, architect, and execute enterprise-grade UI test code.

## What is this?

VelocitAI 是一套 **通用 UI 自动化 Agent Harness**，为 Claude Code / AI Agent 提供：

- **12 个 Skills**：覆盖从生成 PageObject 到运行测试、排查失败的完整工作流
- **8 个 Playwright 规则**：定位符策略、等待策略、断言模式等最佳实践
- **Agent 行为边界**：防止 agent 自行默认环境、自动提交、无声纠偏
- **代码审查代理**：P0/P1/P2 分级审查 + AST 知识图谱分析
- **自我进化机制**：agent 在踩坑后自动沉淀经验到 skills/rules/docs

## Quick Start

1. 将 `.claude/` 和 `CLAUDE.md` 复制到你的 Playwright + pytest 项目根目录
2. 根据项目实际情况修改：
   - `CLAUDE.md` 路由表中的测试命令和路径
   - `.claude/settings.json` 中的权限和 agent-browser URL
   - `.claude/rules/coding-conventions/` 中的角色名和基类名
3. 在 `docs/` 中填入项目的 PageObject 清单和回归测试点

## Structure

```
.claude/
├── settings.json           # 权限 + hooks
├── agents/                 # 子代理定义
├── rules/                  # 强制规则（Must/Must-not）
│   ├── agent-behavior/     # Agent 决策边界
│   ├── coding-conventions/ # 编码规范
│   ├── playwright/         # Playwright 使用规范
│   └── report-strategy/    # 报告生成策略
└── skills/                 # 操作技能（How-to）
    ├── gen-page-test/      # 一键生成 PageObject + 测试
    ├── locator-replacer/   # 六级定位符替换
    ├── test-runner/        # 运行测试 + 结果分析
    ├── quick-debug/        # 免登快速排查
    └── ...                 # 更多 skills
```

## Tech Stack

- Python 3.10+
- Playwright
- pytest + allure
- agent-browser（可选，DOM 探索）
- code-review-graph MCP（可选，AST 图谱）

## License

MIT

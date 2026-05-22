# VelocitAI

**为 AI 编程代理提供的完整 UI 自动化方法论，基于可组合技能和强制规则构建。**

VelocitAI 是一套 Agent Harness（代理治理框架）—— 不是又一个测试框架，而是让 AI 代理能够**自主生成、执行、调试和进化**企业级 UI 测试代码，基于 Python + Playwright + pytest。

> 使用 AI Agent 仅需 15 个工作日，传统人工编码预估 60 个工作日 —— **4 倍开发速度**。

---

## 安装

### Claude Code（推荐）

```bash
claude install-plugin velocitai
```

### Copilot CLI

```bash
# 克隆并复制到你的项目
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{skills,rules,hooks,docs,CLAUDE.md,AGENTS.md} your-project/
```

### Gemini CLI

```bash
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{skills,rules,hooks,docs,CLAUDE.md,GEMINI.md} your-project/
```

### 手动安装

```bash
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{.claude,.claude-plugin,skills,rules,hooks,docs,CLAUDE.md,AGENTS.md,GEMINI.md} your-project/
```

---

## 包含内容

### 13 个技能（How-to）

技能告诉你的代理**如何**完成任务 —— 分步操作指南。

| 技能 | 用途 |
|------|------|
| `ui-automation-harness` | 路由器：将子技能组合成多步骤工作流 |
| `gen-page-test` | 从目标页面生成 PageObject + 测试文件 |
| `add-regression-point` | 为已有页面添加回归测试点 |
| `locator-replacer` | 使用六级优先级替换脆弱定位符（P0 ARIA → P5 XPath） |
| `test-runner` | 运行测试 + 结构化失败分析 |
| `quick-debug` | 三步超时排查：页面 → tab → 定位符 |
| `page-load-assertion` | 用 4 种验证模式设计 `is_page_loaded()` |
| `wait-strategy` | 配置隐式/显式等待策略 |
| `browser-config` | viewport、超时、context、headless/headed |
| `case-round-trip` | 确保测试往返闭合（状态一致性） |
| `save-verify-strategy` | Toast / 重定向 / 数据对比 / 富文本验证 |
| `architecture` | 架构决策、继承设计、角色拆分 |
| `code-review-graph` | AST 知识图谱驱动的代码审查 |

### 14 个规则文件（Must / Must-not）

规则强制硬性约束。每条规则包含 ❌ 反模式 + ✅ 最佳实践。

| 规则域 | 文件数 | 关键规则 |
|--------|--------|---------|
| **Agent 行为** | 3 | 运行测试前确认 `--env`；不自动提交；文档/代码冲突时询问 |
| **编码规范** | 1 | PascalCase 类名、snake_case 方法名、定位符声明为类常量 |
| **Playwright** | 8 | 六级定位符优先级、禁止 `time.sleep()`、context 隔离 |
| **报告策略** | 1 | 仅失败时生成 HTML 报告、自动轮转、域名统计 |

### 1 个子代理

- **code-reviewer**：P0/P1/P2 分级审查 + AST 影响半径分析

### 自我进化机制

VelocitAI 代理从错误中学习。遇到问题后，自动将经验持久化：

| 类型 | 目标 |
|------|------|
| How-to（经验） | `skills/<主题>/SKILL.md` |
| Must/Must-not（规则） | `rules/<规则域>/<规则>.md` |
| 项目事实 | `docs/<文件>.md` |

---

## 工作流

```
1. 探索页面       → agent-browser（相比 Playwright MCP 节省 82-93% token）
2. 生成 PageObject → gen-page-test 技能
3. 编写测试用例    → add-regression-point + case-round-trip
4. 运行 & 调试     → test-runner → quick-debug（自动三步排查）
5. 代码审查        → code-reviewer 代理 + AST 知识图谱
6. 进化沉淀        → 自动持久化到 skills / rules / docs
```

---

## 项目结构

```
velocitai/
├── CLAUDE.md                 # Agent 入口 & 路由表
├── AGENTS.md                 # Copilot CLI 入口
├── GEMINI.md                 # Gemini CLI 入口
├── package.json              # npm 发布配置
├── .claude-plugin/           # Claude Code 插件配置
│   ├── plugin.json
│   └── marketplace.json
├── .claude/                  # Claude 专属配置
│   ├── settings.json         # 权限 + hooks
│   └── agents/               # 子代理定义
│       └── code-reviewer.md
├── skills/                   # 操作技能（How-to）
│   ├── SKILL.md              # 路由器（组合子技能）
│   ├── gen-page-test/
│   ├── locator-replacer/
│   ├── test-runner/
│   ├── quick-debug/
│   └── ... （共 13 个）
├── rules/                    # 强制规则（Must/Must-not）
│   ├── agent-behavior/       # 3 个文件
│   ├── coding-conventions/   # 1 个文件
│   ├── playwright/           # 8 个文件
│   └── report-strategy/      # 1 个文件
├── hooks/                    # 会话与工具 hooks
│   └── hooks.json
└── docs/                     # 项目知识库
    ├── architecture.md
    ├── pages-catalog.md
    ├── regression-points.md
    └── setup.md
```

---

## 兼容的 AI Agent 平台

| 平台 | 状态 | 入口文件 |
|------|------|---------|
| **Claude Code** | 原生支持（插件） | `CLAUDE.md` |
| **GitHub Copilot CLI** | 技能兼容 | `AGENTS.md` |
| **Gemini CLI** | 技能兼容 | `GEMINI.md` |
| **Cursor** | 规则兼容 | `CLAUDE.md` |
| **Windsurf** | 规则兼容 | `CLAUDE.md` |

---

## 技术栈

- **Python 3.10+** — 核心语言
- **Playwright** — 浏览器自动化
- **pytest** — 测试框架
- **Allure** — 测试报告
- **agent-browser** — AI 驱动的浏览器 DOM 探索（可选，Rust CLI）
- **code-review-graph** — AST 知识图谱 MCP（可选）

---

## 快速开始

```bash
# 1. 克隆并集成
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{skills,rules,hooks,docs,.claude,CLAUDE.md} your-project/

# 2. 安装依赖
cd your-project
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 3. 运行测试（--env 必须指定）
pytest tests/ --env=pre

# 4. 查看报告
allure serve reports/allure-results
```

---

## 许可证

MIT

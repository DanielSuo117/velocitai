<div align="center">

# VelocitAI

**[中文](#中文) | [English](#english)**

</div>

---

<a id="中文"></a>

## 中文

**为 AI 编程代理提供的完整 UI 自动化方法论，基于可组合技能和强制规则构建。**

VelocitAI 是一套 Agent Harness（代理治理框架）—— 不是又一个测试框架，而是让 AI 代理能够**自主生成、执行、调试和进化**企业级 UI 测试代码，基于 Python + Playwright + pytest。

> 使用 AI Agent 仅需 15 个工作日，传统人工编码预估 60 个工作日 —— **4 倍开发速度**。

---

### 安装

#### Claude Code（推荐）

```bash
claude install-plugin velocitai
```

#### Copilot CLI

```bash
# 克隆并复制到你的项目
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{skills,rules,hooks,scripts,docs,CLAUDE.md,AGENTS.md} your-project/
```

#### Gemini CLI

```bash
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{skills,rules,hooks,scripts,docs,CLAUDE.md,GEMINI.md} your-project/
```

#### 手动安装

```bash
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{.claude,.claude-plugin,skills,rules,hooks,scripts,docs,CLAUDE.md,AGENTS.md,GEMINI.md} your-project/
```

> **`scripts/` 不可省略**：`hooks/hooks.json` 调的落库校验闸门就在 `scripts/gate_cli.py`。
> 漏拷这一层，hook 会因找不到脚本而静默失效 —— 规则层仍在，但没有强制力。
>
> **Windows 用户**：hook 已自动按 `py -3` → `python3` → `python` 兜底找解释器，
> 装 python.org 官方包（自带 `py` 启动器）即可，不必手改 `hooks/hooks.json`。
> `py` 优先是为了绕开微软商店的 `python`/`python3` 存根。但要装 **Git for Windows**：
> 没装时 Claude Code 用 PowerShell 跑 hook，这段 sh 语法跑不起来，闸门会静默放行
> （fail-open）。Claude Code 本身也推荐装 Git for Windows。

---

### 包含内容

#### 13 个技能（How-to）

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

#### 15 个规则文件（Must / Must-not）

规则强制硬性约束。每条规则包含 ❌ 反模式 + ✅ 最佳实践。

| 规则域 | 文件数 | 关键规则 |
|--------|--------|---------|
| **Agent 行为** | 4 | 运行测试前确认 `--env`；不自动提交；文档/代码冲突时询问 |
| **编码规范** | 1 | PascalCase 类名、snake_case 方法名、定位符声明为类常量 |
| **Playwright** | 8 | 六级定位符优先级、禁止 `time.sleep()`、context 隔离 |
| **报告策略** | 1 | 仅失败时生成 HTML 报告、自动轮转、域名统计 |

#### 1 个子代理

- **code-reviewer**：P0/P1/P2 分级审查 + AST 影响半径分析

#### 自我进化机制

VelocitAI 代理从错误中学习。遇到问题后，自动将经验持久化：

| 类型 | 目标 |
|------|------|
| How-to（经验） | `skills/<主题>/SKILL.md` |
| Must/Must-not（规则） | `rules/<规则域>/<规则>.md` |
| 项目事实 | `docs/<文件>.md` |

---

### 工作流

```
1. 探索页面       → agent-browser（相比 Playwright MCP 节省 82-93% token）
2. 生成 PageObject → gen-page-test 技能
3. 编写测试用例    → add-regression-point + case-round-trip
4. 运行 & 调试     → test-runner → quick-debug（自动三步排查）
5. 代码审查        → code-reviewer 代理 + AST 知识图谱
6. 进化沉淀        → 自动持久化到 skills / rules / docs
```

---

### 项目结构

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
│   ├── rules-index.md        # 规则索引
│   ├── agent-behavior/       # 4 个文件
│   ├── coding-conventions/   # 1 个文件
│   ├── playwright/           # 8 个文件
│   └── report-strategy/      # 1 个文件
├── hooks/                    # 会话与工具 hooks
│   └── hooks.json
├── scripts/                  # 落库校验闸门（零依赖 python3）+ 脚手架
│   ├── gate_cli.py           # 唯一入口，被 hooks.json 调用
│   ├── gate/                 # 校验器 + stdlib unittest 测试
│   └── scaffold_role.py      # 生成 tests/<role>/ 角色骨架
├── docs/                     # 项目知识库
│   ├── architecture.md
│   ├── pages-catalog.md
│   ├── regression-points.md
│   └── setup.md
└── framework/                # 代码部分 —— Python UI 自动化框架
    ├── core/                 # 框架核心
    │   ├── base/             # BasePage · BaseComponent · BaseTest
    │   ├── healing/          # 选择器自愈（拦截器 · 引擎 · 运行时 · 模型 · 写回）
    │   ├── exceptions.py
    │   └── logger.py
    ├── pages/                # 业务页面对象 <name>_page.py（继承 BasePage）
    │   └── components/       # 跨页面复用组件（继承 BaseComponent）
    ├── tests/                # 业务用例，按角色分目录
    │   └── <role>/           # <role>_base_test.py + test_<role>_flow.py
    ├── data/                 # 测试数据 <role>/<feature>.json（utils.data_loader 读取）
    ├── utils/                # 业务无关小工具
    ├── config/               # 环境与浏览器配置
    └── conftest.py           # fixture 层 + 失败截图附进 allure
```

> **代码与 harness 分开存放**：上面 `framework/` 之外的部分都是 harness ——
> 治理 agent 行为的技能、规则、闸门与文档。harness 留在仓库根，是因为
> Claude Code 以根级 `.claude-plugin/` 或 `skills/<name>/SKILL.md` 识别插件，
> 挪进子目录会让插件无法被发现。
>
> 安装到你自己的项目时，拷贝的正是 harness 部分；`framework/` 是代码侧的
> 参考实现，按需取用。

---

### 兼容的 AI Agent 平台

| 平台 | 状态 | 入口文件 |
|------|------|---------|
| **Claude Code** | 原生支持（插件） | `CLAUDE.md` |
| **GitHub Copilot CLI** | 技能兼容 | `AGENTS.md` |
| **Gemini CLI** | 技能兼容 | `GEMINI.md` |
| **Cursor** | 规则兼容 | `CLAUDE.md` |
| **Windsurf** | 规则兼容 | `CLAUDE.md` |

---

### 技术栈

- **Python 3.10+** — 核心语言
- **Playwright** — 浏览器自动化
- **pytest** — 测试框架
- **Allure** — 测试报告
- **agent-browser** — AI 驱动的浏览器 DOM 探索（可选，Rust CLI）
- **code-review-graph** — AST 知识图谱 MCP（可选）

---

### 快速开始

```bash
# 1. 克隆并集成
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{skills,rules,hooks,scripts,docs,.claude,CLAUDE.md} your-project/

# 2. 安装依赖
cd your-project
python -m venv .venv && source .venv/bin/activate
# Windows：Git Bash 用 source .venv/Scripts/activate；PowerShell 用 .venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium

# 3. 运行测试（--env 必须指定）
pytest framework/tests/ --env=pre

# 4. 查看报告
allure serve reports/allure-results
```

---

### 许可证

MIT

<br>

**[⬆ 回到顶部](#velocitai) | [Switch to English ⬇](#english)**

---

<a id="english"></a>

## English

**A complete UI automation methodology for your coding agents, built on composable skills and enforced rules.**

VelocitAI is an agent harness — not another test framework — that gives AI agents the ability to **autonomously generate, execute, debug, and evolve** enterprise-grade UI test code using Python + Playwright + pytest.

> 15 working days with AI Agent vs. 60 working days manual coding — **4x development speed**.

---

### Installation

#### Claude Code (recommended)

```bash
claude install-plugin velocitai
```

#### Copilot CLI

```bash
# Clone and copy to your project
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{skills,rules,hooks,scripts,docs,CLAUDE.md,AGENTS.md} your-project/
```

#### Gemini CLI

```bash
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{skills,rules,hooks,scripts,docs,CLAUDE.md,GEMINI.md} your-project/
```

#### Manual Setup

```bash
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{.claude,.claude-plugin,skills,rules,hooks,scripts,docs,CLAUDE.md,AGENTS.md,GEMINI.md} your-project/
```

> **Do not drop `scripts/`**: the sediment validation gate wired up by
> `hooks/hooks.json` lives in `scripts/gate_cli.py`. Without it the hook silently
> does nothing — the rule layer survives, its enforcement does not.
>
> **Windows**: the hook already falls back through `py -3` → `python3` → `python`,
> so the python.org installer (which ships the `py` launcher) is enough — no edit
> to `hooks/hooks.json` needed. `py` goes first to skip the Microsoft Store
> `python`/`python3` stubs.
> Do install **Git for Windows**: without it Claude Code runs hooks under
> PowerShell, this sh syntax cannot run, and the gate silently allows everything
> (fail-open). Claude Code itself recommends Git for Windows.

---

### What's Inside

#### 13 Skills (How-to)

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

#### 15 Rule Files (Must / Must-not)

Rules enforce hard constraints. Every rule includes ❌ anti-pattern + ✅ best practice.

| Domain | Files | Key Rules |
|--------|-------|-----------|
| **Agent Behavior** | 4 | Confirm `--env` before tests; no auto-commit; ask on doc/code conflict |
| **Coding Conventions** | 1 | PascalCase classes, snake_case methods, locator class constants |
| **Playwright** | 8 | 6-level locator priority, no `time.sleep()`, context isolation |
| **Report Strategy** | 1 | HTML report only on failure, auto-rotation, domain stats |

#### 1 Sub-Agent

- **code-reviewer**: P0/P1/P2 graded review + AST impact radius analysis

#### Self-Evolution

VelocitAI agents learn from mistakes. After encountering issues, they automatically persist learnings:

| Type | Target |
|------|--------|
| How-to (experience) | `skills/<topic>/SKILL.md` |
| Must/Must-not (rule) | `rules/<domain>/<rule>.md` |
| Project facts | `docs/<file>.md` |

---

### Workflow

```
1. Explore page       → agent-browser (82-93% token savings vs Playwright MCP)
2. Generate PageObject → gen-page-test skill
3. Write test cases    → add-regression-point + case-round-trip
4. Run & debug         → test-runner → quick-debug (auto 3-step triage)
5. Code review         → code-reviewer agent + AST knowledge graph
6. Evolve              → auto-persist to skills / rules / docs
```

---

### Project Structure

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
│   ├── rules-index.md        # Rule index
│   ├── agent-behavior/       # 4 files
│   ├── coding-conventions/   # 1 file
│   ├── playwright/           # 8 files
│   └── report-strategy/      # 1 file
├── hooks/                    # Session & tool hooks
│   └── hooks.json
├── scripts/                  # Sediment validation gate (zero-dependency python3) + scaffolding
│   ├── gate_cli.py           # Single entry point, invoked by hooks.json
│   ├── gate/                 # Checkers + stdlib unittest suite
│   └── scaffold_role.py      # Generates the tests/<role>/ skeleton
├── docs/                     # Project knowledge base
│   ├── architecture.md
│   ├── pages-catalog.md
│   ├── regression-points.md
│   └── setup.md
└── framework/                # Code side — the Python UI automation framework
    ├── core/                 # Framework core
    │   ├── base/             # BasePage · BaseComponent · BaseTest
    │   ├── healing/          # Selector self-healing (interceptor · engine · runtime · llm · patcher)
    │   ├── exceptions.py
    │   └── logger.py
    ├── pages/                # Business page objects <name>_page.py (extend BasePage)
    │   └── components/       # Reusable cross-page components (extend BaseComponent)
    ├── tests/                # Business test cases, one directory per role
    │   └── <role>/           # <role>_base_test.py + test_<role>_flow.py
    ├── data/                 # Test data <role>/<feature>.json (read via utils.data_loader)
    ├── utils/                # Business-agnostic helpers
    ├── config/               # Environment and browser configuration
    └── conftest.py           # Fixture layer + failure screenshots attached to allure
```

> **Code and harness are stored separately.** Everything outside `framework/`
> is the harness — the skills, rules, gate and docs that govern agent behaviour.
> The harness stays at the repo root because Claude Code identifies a plugin by
> a root-level `.claude-plugin/` directory or `skills/<name>/SKILL.md`; moving
> `skills/` into a subdirectory would make the plugin undiscoverable.
>
> When installing into your own project you copy the harness; `framework/` is
> the reference implementation of the code side, to adopt as needed.

---

### Compatible Agents

| Platform | Status | Entry File |
|----------|--------|------------|
| **Claude Code** | Native support (plugin) | `CLAUDE.md` |
| **GitHub Copilot CLI** | Skills compatible | `AGENTS.md` |
| **Gemini CLI** | Skills compatible | `GEMINI.md` |
| **Cursor** | Rules compatible | `CLAUDE.md` |
| **Windsurf** | Rules compatible | `CLAUDE.md` |

---

### Tech Stack

- **Python 3.10+** — Core language
- **Playwright** — Browser automation
- **pytest** — Test framework
- **Allure** — Test reporting
- **agent-browser** — AI browser DOM exploration (optional, Rust CLI)
- **code-review-graph** — AST knowledge graph MCP (optional)

---

### Quick Start

```bash
# 1. Clone and integrate
git clone https://github.com/DanielSuo117/velocitai.git
cp -r velocitai/{skills,rules,hooks,scripts,docs,.claude,CLAUDE.md} your-project/

# 2. Install dependencies
cd your-project
python -m venv .venv && source .venv/bin/activate
# Windows: Git Bash `source .venv/Scripts/activate`; PowerShell `.venv\Scripts\Activate.ps1`
pip install -r requirements.txt
playwright install chromium

# 3. Run tests (--env is REQUIRED)
pytest framework/tests/ --env=pre

# 4. View report
allure serve reports/allure-results
```

---

### License

MIT

<br>

**[⬆ Back to top](#velocitai) | [切换到中文 ⬆](#中文)**

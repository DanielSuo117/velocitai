# Harness 落库校验闸门 — 设计文档

> 状态：待实现 · 日期：2026-09-19 · 上游需求：防止自我进化机制沉淀垃圾数据劣化 agent 编码质量

---

## 1. 背景与问题

VelocitAI 的自我进化机制（CLAUDE.md「自我进化机制（P0 最高优先级）」章节）要求 agent 在踩坑、被纠正、任务完成时把经验沉淀到 `skills/` / `rules/` / `docs/`。当前该机制**只有一句执行约定**：

```
执行：Edit 最小增量写入；回复末尾声明 `📝 已沉淀至 <file>：<摘要>`。
```

没有任何校验闸门。后果是 agent 可以把一次性结论、推测、常识、与既有规则重复或矛盾的内容写进库。这些内容随后会被**每一个新会话加载为高优先级上下文**，直接劣化 agent 的实际编码行为 —— 垃圾数据在这套架构里不是静态污染，而是会自我强化的负反馈。

本设计为落库建立一道闸门。

## 2. 范围

**本轮交付**：harness 落库校验闸门（规则层 + 校验层 + 接线层）。

**明确不在本轮**：LLM 选择器自愈机制。它是独立子系统，单独走 spec → plan → 实现。两者的依赖方向是单向的 —— 自愈产出的新选择器回写 PageObject 与 `docs/regression-points.md` 时同样是一次落库，应复用本轮建成的闸门，因此闸门先建。

**非目标**：
- 不提供面向用户的"全量体检"功能（`--mode audit` 仅作为测试与 commit 模式的内部入口，不对外宣传）
- 不追究存量违规（见 §9.3）
- 不解决 Windows 下 `python3` 解释器名差异（见 §13）

## 3. 架构：三层职责

| 层 | 产物 | 对谁生效 | 职责 |
|---|---|---|---|
| 规则层 | `rules/agent-behavior/evolution-gate.md` | Claude / Copilot / Gemini 全部 | 唯一事实源：定义什么配落库，含证据门槛与去重要求 |
| 校验层 | `scripts/gate/` | 任何有 python3 的环境 | 规则层中可确定性判定部分的可执行子集 |
| 接线层 | `hooks/hooks.json` | 仅 Claude Code | 把校验结果传导为硬阻断 / 强制询问 |

**降级链**：任一层缺失都能独立运行。未安装 hook → 规则层仍约束 agent；换用 Copilot/Gemini → 规则层仍生效；脚本异常 → fail-open 放行，规则层兜底。

**核心设计原则 —— fail-open**：闸门宁可漏判也绝不阻塞正常工作。一个会把人卡死的质量工具，最终一定会被关掉。

## 4. 文件结构

```
scripts/
├── gate_cli.py                  # 唯一入口，自带 sys.path 引导；hook / 人 / CI 共用
└── gate/
    ├── __init__.py
    ├── violation.py             # Violation 契约 + Severity（唯一跨模块数据结构）
    ├── context.py               # 定位仓库根；路径归类；gitignore 查询
    ├── runner.py                # 三种模式的编排：决定跑哪些 checker、喂什么内容
    ├── checkers/
    │   ├── __init__.py          # CHECKERS 有序注册表
    │   ├── structure.py         # 维度② 结构合规
    │   ├── genericity.py        # 维度③ 通用化检测
    │   ├── registry.py          # 维度④ 注册闭环 + 镜像弃用守卫
    │   └── evidence.py          # 维度① 证据门槛与去重
    └── tests/                   # stdlib unittest
        ├── test_structure.py
        ├── test_genericity.py
        ├── test_registry.py
        ├── test_evidence.py
        ├── test_runner.py
        ├── test_hook_contract.py
        ├── test_baseline.py     # 零误报回归基线（见 §11）
        └── fixtures/
```

**为什么测试用 stdlib unittest 而非 pytest**：根 `conftest.py` 的 `--env` 选项是 `required=True`，对 rootdir 下任何 pytest 调用都生效，`pytest scripts/` 会被迫要求传 `--env`；且 `tests/` 是分发给使用者的 Playwright 模板目录，不应混入 harness 自身的测试。unittest 零依赖、零耦合，与「stdlib only」原则一致。

**依赖约束**：`scripts/gate/` 只允许使用 Python 3 标准库。不得引入第三方依赖 —— 它随插件分发，运行环境不可控。

## 5. Violation 契约

```python
class Severity(enum.IntEnum):
    WARN = 1
    ASK = 2
    BLOCK = 3

@dataclass(frozen=True)
class Violation:
    code: str            # 稳定机器码 STR001 / GEN003 …；规则文档按码索引
    severity: Severity
    path: str            # 相对仓库根
    line: int | None     # 命中行号，无则 None
    message: str         # 违反了什么
    fix: str             # 怎么改
```

`fix` 是设计核心：闸门不只说「不行」，而是把可执行的改法原样写入 `permissionDecisionReason` 回传给 agent，使其能自行改正后重写，而不是卡住来问人。

**聚合规则**：一次调用产生的所有 Violation 取最高 severity 决定动作，`BLOCK > ASK > WARN`。

**Severity 到 hook 行为的映射**：

| Severity | 退出码 | stdout JSON | 效果 |
|---|---|---|---|
| BLOCK | 2 | `permissionDecision: "deny"` + 理由 | 拦下，理由喂回 agent |
| ASK | 0 | `permissionDecision: "ask"` + 提案要素清单 | 触发 Claude Code 原生用户授权弹窗 |
| WARN | 0 | 无决策 | 写 stderr，不阻塞 |
| 无违规 | 0 | 无输出 | 静默放行 |

**ASK 是本设计的关键机制**：用户选定的「新建必确认」策略，通过 `permissionDecision: "ask"` 由 Claude Code 强制执行，而非依赖 agent 自觉先提案。agent 无法绕过。

## 6. Checker 码表

### 6.1 structure.py — 结构合规

作用域：`skills/**/SKILL.md`、`rules/**/*.md`、`docs/*.md`（**不含 `docs/superpowers/**`**，见下方豁免）

| 码 | 判定 | 级别 |
|---|---|---|
| STR001 | `skills/*/SKILL.md` 缺 YAML frontmatter，或缺 `name` / `description` 字段 | BLOCK |
| STR002 | frontmatter `name` ≠ 所在目录名 | BLOCK |
| STR003 | `rules/**/*.md` 缺 ❌ 或缺 ✅ | BLOCK |
| STR004 | Markdown 相对链接指向不存在的路径 | BLOCK |
| STR005 | 文件行数 > 300 | WARN |
| STR006 | 文件行数 > 500 | BLOCK |

**豁免（由 §14 实测数据推导，缺一即产生假违规）**：

- STR002 豁免 `skills/SKILL.md` —— 该文件 `name` 为 `ui-automation-harness` 而目录名为 `skills`，是路由 skill，为唯一例外。
- STR003 豁免索引类文件，判定为文件名匹配 `*-index.md` 或 `*-overview.md` —— `rules/rules-index.md` 与 `rules/playwright/playwright-overview.md` 是纯链接索引，天然无正反例。
- **全部 STR 检查豁免 `docs/superpowers/**`** —— 该目录存放 brainstorming 与 writing-plans 产出的 spec 和 plan，是长篇流程文档而非 harness 知识，体量天然超标。实测：本设计文档 316 行触发 STR005，`2026-05-23-i18n-merge.md` 408 行触发 STR005，而实现计划通常超过 500 行会触发 STR006 —— 不豁免则闸门会把自己的设计文档与实现计划判为违规，无法写入。
- STR004 豁免被 `.gitignore` 忽略的目标路径 —— `CLAUDE.md` 链接到的 `./CLAUDE.local.md` 是设计上可选的私有备忘（见 CLAUDE.md 末行「私有备忘：CLAUDE.local.md（不入库）」），不存在属正常状态，不得判为死链。

**阈值依据**：现有 26 个 harness 文件最大 208 行，均值约 109 行。300 / 500 对现有库留有充足余量。

### 6.2 genericity.py — 通用化检测

> **实现期修正（2026-09-19）**
> 1. `/home/` 不在本节列出的前缀内，实现时被误加，导致 `page.goto("/home/dashboard")`
>    这类普通站内路由被判 GEN002 **BLOCK**。已移除，前缀恢复为 `/Users/`、`/Applications/`、`C:\`。
> 2. 绝对路径正则尾部由 `*` 改为 `+`：裸前缀「`/Users/` 开头的绝对路径」属描述性提及，
>    不是路径本身，判成违规是误报。
> 3. 反例教学豁免扩展到 GEN001–GEN004（原仅 GEN003/GEN004）。起因：本项目规范要求
>    每条规则配 ❌ 反例，含 P0.5「skill 正文不得写入项目专有标识」这一条本身 ——
>    只豁免 GEN003 时，闸门会拦下它自己要求人写的那个反例。
> 4. 但两组用的判据**宽窄不同**。`_is_teaching_line`（宽：`#` 标题、`|` 表格行、
>    清单项、显式标记）仅供 GEN003/GEN004 使用；GEN001/GEN002 改用
>    `_is_counterexample_line`（窄：仅 ❌ / BAD / 禁止）。
>    原因：把结构前缀整体豁免，会让 GEN001/GEN002 对**表格行与 Markdown 标题中的
>    硬编码 URL 与绝对路径彻底失明**，而表格在本项目 skills 正文里极其常见 ——
>    堵住项目专有标识正是这两条检查存在的唯一理由。

作用域：仅 `skills/**`（对应既有规则 P0.5「Skill 正文不得写入项目专有标识」）

| 码 | 判定 | 级别 |
|---|---|---|
| GEN001 | 出现具体 URL / 域名 | BLOCK |
| GEN002 | 出现本地绝对路径（`/Users/`、`/Applications/`、`C:\`） | BLOCK |
| GEN003 | 出现真实哈希类名赋值 | BLOCK |
| GEN004 | 命中自定义业务术语黑名单 `scripts/gate/wordlist.txt` | WARN |

**GEN001 白名单**：`example.com`、纯占位 `https://...`、`github.com/DanielSuo117/velocitai`、`docs.claude.com`、`code.claude.com`、`playwright.dev`。

**GEN003 误报边界 —— 本设计中风险最高的一处判定**：`skills/locator-replacer/SKILL.md` 中哈希类名字面量出现 7 次、`rules/playwright/locator-strategy.md` 中 1 次，全部是「这些不能用」的反例教学。天真正则会把讲解哈希类名危害的文档判定为使用哈希类名。

判定收窄为：命中行须形如**真实赋值**，即同时满足：
- 行首去空白后不以 `#` 开头（排除代码注释）
- 行首去空白后不以 `|` 开头（排除表格行）
- 行首去空白后不以 `- [ ]` 开头（排除检查清单）
- 整行不含 `BAD`、`❌`、`禁止` 任一标记

按此规则，现有 8 处命中全部豁免，零误报。

**GEN003 的第二条判别（实现期发现，spec 补订）**：哈希类名的正则本身还必须**要求哈希段含数字**。仅按「下划线分段」匹配会命中 `.is_page_loaded`、`.set_default_timeout` 等 Python 方法名 —— 实测在本仓库 skills 正文中造成 36 处误报。构建工具哈希段必含数字（`abc123` / `1x2y3` / `1a2b3c`），而方法名每段纯字母，这是可靠的区分点。

**GEN004 的 `wordlist.txt` 默认为空**。项目专有业务术语无法通用检测，由使用者按自己项目填写；空文件时该检查静默跳过。

### 6.3 registry.py — 注册闭环与镜像弃用守卫

| 码 | 判定 | 级别 | 运行模式 |
|---|---|---|---|
| REG001 | `skills/<name>/SKILL.md` 存在，但 CLAUDE.md 路由表无指向 `./skills/<name>/` 的条目 | BLOCK | 仅 commit |
| REG002 | CLAUDE.md 路由表中的链接指向不存在的路径 | BLOCK | 仅 commit |
| REG003 | 写入 `zh/**` 或 `en/**` | BLOCK | write |

**REG001 的注册判定必须匹配真实链接目标（实现期发现，spec 补订）**：不得用全文子串匹配 `./skills/<name>/`。实测该写法双向失效 —— 正文里一句顺带提及即可满足检查（假阴性，REG001 形同虚设），而合法的无尾斜杠写法 `[foo](./skills/foo)` 反被判为未注册（假阳性）。正确做法是用链接正则提取真实的 `](...)` 目标、归一化尾斜杠后再比对。

**REG001 / REG002 为何只在 commit 模式运行**：新建 skill 必然是 `SKILL.md` 先写、CLAUDE.md 路由表后写。挂在写入前会把每一次正常新建都拦死。commit 时两边都已写完，是正确的校验时机。

**REG003 的背景**：`zh/` 与 `en/` 是 i18n 合并前的历史副本（根 `index.html` 已完成单文件双语合并，含 274 处 `data-lang` 标记；两个镜像目录下的 `index.html` 均为 0 处标记的合并前版本）。两个目录在删除前由守卫拦住任何新增写入，防止不同步继续扩大。目录删除见 §12.4。

### 6.4 evidence.py — 证据门槛与去重

| 码 | 判定 | 级别 |
|---|---|---|
| EVI001 | 在 `skills/` 或 `rules/` 下**新建**文件 | ASK |
| EVI002 | 文件含 `## …P<数字>` 条款小节，但全文无 `**触发**：` 行 | BLOCK |
| EVI003 | 单个条款小节内部无 `**触发**：` 行 | WARN |
| EVI004 | 新增 `##` 标题与库内已有标题词元重叠率 ≥ 0.6 | WARN |

**EVI001 的 ASK 理由文案**须包含提案要素清单：触发条件、失败现象、拟写入位置、与哪条既有规则相关。

**EVI002 为何是文件级而非条款级**：实测 16 个 `P<数字>` 条款中有 3 个（`skill-authoring.md` 的 P0.5 / P0.6 / P0.7）无条款级触发行，因该文件在开头写有覆盖全文的**文件级** `**触发**：新建 / 修改 skills/**/SKILL.md`。若按条款级设 BLOCK，现有库立即产生 3 条假违规。故 BLOCK 卡文件级（现有库 100% 通过），条款级仅 WARN（现有库 3 条提醒，可接受）。

**EVI002 是「证据门槛」的可执行化落点**：`**触发**：` 是项目既有书写约定，闸门只是开始执行它。没有触发条件的规则，就是没有证据的规则。

**EVI004 的定位**：语义去重只能做弱信号。标题归一化（去标点、去 emoji、去 P 级编号）后按词元集合计算 Jaccard 重叠率，命中给 WARN 并指出疑似重复的 `<file>:<line>`，提示「考虑合并而非新增」。硬判定由规则层 P0.8 与 EVI001 的人工确认承担。

## 7. 运行模式

| 模式 | 触发 | 校验范围 | 启用的 checker |
|---|---|---|---|
| `--mode write` | PreToolUse on Write/Edit | 单个目标文件 | structure、genericity、evidence、REG003 |
| `--mode commit` | PreToolUse on Bash(git commit *) | `git diff --cached --name-only` 涉及的文件 | 全部，含 REG001 / REG002 |
| `--mode audit` | 测试与内部调用 | 全仓库 | 全部 |

## 8. hook 接线

`hooks/hooks.json` 目标内容：

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Write|Edit",
        "hooks": [{ "type": "command", "timeout": 10,
          "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/gate_cli.py\" --mode write" }] },
      { "matcher": "Bash",
        "hooks": [
          { "type": "command", "if": "Bash(git commit *)", "timeout": 20,
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/gate_cli.py\" --mode commit" },
          { "type": "command", "if": "Bash(git commit *)", "timeout": 30,
            "command": "code-review-graph build" }
        ] }
    ],
    "SessionStart": [
      { "matcher": "", "hooks": [{ "type": "command", "command": "code-review-graph status", "timeout": 10 }] }
    ]
  }
}
```

**写入 hook 不使用 `if` 做路径预过滤**。需覆盖 `Write` × `Edit` × 多个路径前缀的组合，用 `if` 会拆成大量 handler，且 permission-rule 的路径通配语义不足以支撑设计确定性。改为 `matcher: "Write|Edit"` 全接、脚本首步分类路径、无关文件立即 `exit 0`。代价为每次文件编辑增加约 50ms python 启动开销，可接受。

**`${CLAUDE_PLUGIN_ROOT}`** 由 Claude Code 提供，解析为插件安装目录绝对路径，使脚本随插件分发后仍可被稳定寻址。

## 9. 实现契约

### 9.1 Edit 场景需重建全文

hook 的 `tool_input` 中，`Write` 提供 `content`（最终全文），但 `Edit` 只提供 `old_string` / `new_string`。Edit 分支必须：读取磁盘现有内容 → 应用一次 `old_string` → `new_string` 替换 → 得到预期全文后再校验。若替换匹配不上（文件已变更），fail-open `exit 0`。

### 9.2 「新建」的判定

`tool_name == "Write"` 且 `tool_input.file_path` 在磁盘上不存在。Edit 必然作用于已有文件，天然不触发 EVI001。

### 9.3 commit 模式不追究存量

若 commit 前做全量校验，`browser-tool-usage.md` 的存量违规（§12.1）会阻断**每一次** commit。故 commit 模式只校验本次暂存区涉及的文件；REG001 / REG002 这类全局检查亦只在暂存区涉及 `skills/` 或 `CLAUDE.md` 时才运行。

### 9.4 fail-open 的实现要求

`gate_cli.py` 顶层须捕获全部异常，记录到 stderr 后 `exit 0`。任何 checker 抛出的异常不得逃逸到退出码。

**fail-open 的「方向」同样是契约的一部分（实现期发现，2026-09-19 修正）。**
异常被捕获还不够，捕获后返回什么值决定了它到底 fail-open 还是 fail-closed。
`git_ignored()` 原本在异常时 `return False`，而两个调用点都把 False 读作
「未被忽略 → 报违规」—— 于是一次 git 超时就会让 `CLAUDE.local.md` 的豁免失效，
产出伪 REG002 并**拦死 `git commit`**。这是字面意义上的 fail-closed。

现契约：

| `git check-ignore` 结果 | `git_ignored()` | 理由 |
|---|---|---|
| 退出码 0（确为忽略） | `True` | 事实 |
| 退出码 1（确非忽略） | `False` | **唯一**返回 False 的分支 |
| 退出码 128 / 超时 / 异常 | `True` | 未知即豁免 |

**代价（已接受）**：在非 git 仓库中 `check-ignore` 返回 128，于是 STR004 / REG002
在仓库外一律失效。这是 fail-open 的正确读法，但确实是一处覆盖损失，记录备查。

## 10. 规则层与入口改动

| 文件 | 操作 | 内容 |
|---|---|---|
| `rules/agent-behavior/evolution-gate.md` | 新建 | frontmatter `paths: ["skills/**", "rules/**", "docs/**"]` 懒加载；P0.8 沉淀前必须检索去重；P0.9 沉淀必须带触发条件与失败现象；P0.10 新建 skill/rule 必须先提案后落库；附 Violation 码表（每码一句含义 + 一句修法） |
| `rules/agent-behavior/agent-behavior.md` | 修改 | 末尾加一行引出，沿用既有 `P0.5–P0.7 → skill-authoring.md` 的懒加载写法 |
| `CLAUDE.md` | 修改 | 路由表新增「**落库校验** / 沉淀闸门」行；自我进化机制章节补充「先过闸门 + 新建需用户确认」 |
| `AGENTS.md` | 修改 | 自我进化机制章节加入同一条引用 |
| `GEMINI.md` | 修改 | 同上 |

`AGENTS.md` / `GEMINI.md` 对应的 agent 吃不到 hook，规则层是它们唯一的约束途径。

**自洽要求**：`evolution-gate.md` 自身必须通过 STR003（含 ❌ 反例与 ✅ 正例）与 EVI002（含 `**触发**：` 行）。闸门的规则文件必须能通过自己定义的闸门。

## 11. 测试与验收

```bash
python3 -m unittest discover -s scripts/gate/tests -v
```

每个 checker 一个测试文件配 fixtures，另有两个跨切面测试：

**`test_hook_contract.py`** —— 构造 stdin JSON 喂给 `gate_cli.py`，断言退出码与 stdout JSON 结构，覆盖 BLOCK / ASK / WARN / 放行四种路径。

**`test_baseline.py` —— 零误报回归基线（最关键）**：对当前整个仓库跑 `--mode audit`，断言 **§12 存量修复完成后** BLOCK 总数为 1，且唯一一条是 `rules/agent-behavior/browser-tool-usage.md` 的 STR003（该条在 §12.1 修复后归零，届时基线断言改为 0）。实现顺序上，本测试须在 §12.1 与 §12.3 之后接入。§14 三轮实测得出的每一条豁免规则，都由这个测试固化为可执行断言。将来任何人修改 checker 正则引入误报，此测试立即失败。

**验收标准**：
1. 全部 unittest 通过
2. `test_baseline.py` 断言成立
3. 手工验证：新建一个 `skills/` 下的文件触发 ASK 弹窗；写入含真实哈希类名赋值的 skill 触发 BLOCK 并回传 fix；编辑 `pages/base_page.py` 静默放行

## 12. 存量修复

### 12.1 `browser-tool-usage.md` 补 ❌ 反例
该文件有 5 处 ✅ 正例、0 处 ❌ 反例，违反 CLAUDE.md「规则必含 ❌反例 + ✅正例」。它不是索引文件，是闸门查出的第一条真实存量违规。

### 12.2 `hooks/hooks.json` schema 与 matcher 修复
两处偏离官方 plugin hooks 规范，导致插件用户装上后现有两个 hook 很可能从未生效：
- 顶层 `"hooks"` 当前是**数组** + 每项 `"type": "PreToolUse"`；规范要求是按事件名分键的**对象**
- `"matcher": "Bash(git commit *)"` —— matcher 只匹配工具名，须拆为 `"matcher": "Bash"` + handler 上的 `"if": "Bash(git commit *)"`

不修复则新闸门挂上去会以同样方式失效。`.claude/settings.json` 中的对应配置格式正确，可作参照。

### 12.3 修复 8 条死链
`skills/` 下 6 个 SKILL.md 共 8 处链接写作 `../../../docs/...`，跳出了仓库。这是从 `.claude/skills/` 迁移到 `skills/` 时漏改的路径深度 —— 旧布局下 `../../../` 恰为仓库根，新布局下多跳一层。正确写法为 `../../docs/...`。

涉及：`gen-page-test`(1)、`locator-replacer`(1)、`add-regression-point`(2)、`architecture`(2)、`case-round-trip`(2)。

这 8 条是闸门 STR004 查出的存量违规，须在 `test_baseline.py` 接入前修复。

### 12.4 删除 `zh/` 与 `en/`
两者为 i18n 合并前的历史副本。**执行前须再次向用户确认** —— 不可逆的目录删除，且涉及 88 个已入库文件。

## 13. 已知风险与遗留

**Windows 解释器名**：`python3` 在 Windows 上常只作 `python`。解释器缺失 → hook 执行失败 → Claude Code 视为无决策 → 放行。行为符合 fail-open 设计，不会卡住用户，但闸门在这些机器上静默失效。README 注明，本轮不解决。

**`.gitignore` 与 `.claude-plugin` 的冲突**：`.gitignore` 含 `.claude-plugin` 条目，但该目录下 6 个文件早已入库，ignore 对它们无效；将来往 `.claude-plugin/` 新增文件会被静默忽略。与本轮无关，记录备查。

**WARN 的可见性（已结案，2026-09-19）**：实测确认宿主在退出码 0 时从 **stdout**
构造 hook 提示，stderr 不被呈现 —— 即原方案下 4 个 WARN 码（STR005 / GEN004 /
EVI003 / EVI004）在写入期实际不可见。现方案：top severity 为 WARN 时，向 stdout
输出 `{"systemMessage": "落库校验提示：…"}`（宿主文档明确该字段对所有 hook 生效），
并保留 stderr 副本；与 ASK / BLOCK 混合时 WARN 同样随决策一并输出，不再被吞。
Windows 解释器名的说明已写入 README。

## 14. 实测依据

设计中每条阈值与豁免均来自对当前仓库的实测，而非直觉估计。

**skill frontmatter `name` 与目录名**：12 个子 skill 全部一致；`skills/SKILL.md` 为唯一不一致（`ui-automation-harness` vs `skills`）→ 推出 STR002 豁免。

**rules 文件 ❌ / ✅ 覆盖**：14 个文件中 11 个通过。3 个未通过者中，`rules-index.md` 与 `playwright-overview.md` 为纯索引 → 推出 STR003 豁免；`browser-tool-usage.md`（❌=0，✅=5）为真实存量违规 → §12.1。

**`P<数字>` 条款的 `**触发**：` 覆盖**：16 个条款中 13 个有条款级触发行，缺失的 3 个（`skill-authoring.md` P0.5–P0.7）有文件级触发行 → 推出 EVI002 文件级 / EVI003 条款级的分级。

**skills 中的 URL 与绝对路径**：共 3 处命中，全部为 `https://example.com/xxx` 或占位 `https://...` → 推出 GEN001 白名单，存量零违规。

**哈希类名字面量分布**：`skills/` 7 处 + `rules/` 1 处，全部位于 `# BAD:` 注释、表格行或 `- [ ]` 清单行等反例教学语境 → 推出 GEN003 的四条收窄条件，存量零误报。

**Markdown 链接完整性**：全量扫描 skills / rules / docs / 三个入口文件，命中 9 条不可达链接。其中 8 条为真实断链（§12.3），1 条为 `CLAUDE.md` → `./CLAUDE.local.md` 的设计内可选文件 → 推出 STR004 的 gitignore 豁免。

**路由表注册闭环**：12 个 skill 在 CLAUDE.md 路由表中全部已注册，REG001 存量零违规。

**`docs/superpowers/` 体量实测**：spec 316 行、`2026-05-23-i18n-merge.md` 408 行、`2026-05-22-harness-sync-and-generalize.md` 245 行 → 推出该目录的全量 STR 豁免。

**文件体量分布**：26 个文件合计 2836 行，最大 208 行（`skills/page-load-assertion/SKILL.md`）→ 推出 STR005 = 300 行、STR006 = 500 行。

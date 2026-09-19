# Harness 落库校验闸门 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 VelocitAI 的自我进化机制建立一道落库闸门，阻止一次性结论、推测、重复内容与项目专有标识写入 `skills/` / `rules/` / `docs/`。

**Architecture:** 三层。规则层 `rules/agent-behavior/evolution-gate.md` 是唯一事实源，对所有 agent 生效；校验层 `scripts/gate/` 是规则中可确定性判定部分的可执行子集；接线层 `hooks/hooks.json` 把校验结果传导为 Claude Code 的 deny / ask。任一层缺失都能降级运行，脚本异常一律 fail-open 放行。

**Tech Stack:** Python 3 标准库（禁止第三方依赖）、stdlib unittest、Claude Code plugin hooks、Markdown。

**Spec:** [docs/superpowers/specs/2026-09-19-evolution-gate-design.md](../specs/2026-09-19-evolution-gate-design.md)

## Global Constraints

- `scripts/gate/` **只允许 Python 3 标准库**。不得引入任何第三方依赖 —— 它随插件分发，运行环境不可控。
- **fail-open 是硬约束**：`gate_cli.py` 顶层必须捕获全部异常，记 stderr 后 `exit 0`。任何 checker 抛出的异常不得逃逸到退出码。宁可漏判，绝不阻塞。
- 测试一律用 **stdlib unittest**，禁止 pytest。根 `conftest.py` 的 `--env` 是 `required=True`，对 rootdir 下任何 pytest 调用都生效。
- **本项目 P0.3：agent 不得执行 `git commit` / `git push`。** 本计划每个 Commit 步骤的产物是「提议的 commit message」，由用户自行执行。执行者不得自行提交。
- `skills/**` 正文不得出现项目专有标识（既有规则 P0.5）。
- `rules/**` 新建文件必须同时含 ❌ 反例与 ✅ 正例（CLAUDE.md 自我进化机制章节要求，亦即本闸门的 STR003）。
- 违规码命名固定为 `STR###` / `GEN###` / `REG###` / `EVI###`，与 spec §6 一一对应，不得改名 —— 规则文档按码索引。

---

## 文件结构

| 操作 | 文件 | 职责 |
|------|------|------|
| Create | `scripts/gate_cli.py` | 唯一入口。解析 `--mode`、读 stdin、调 runner、按 Severity 输出 hook 协议 |
| Create | `scripts/gate/__init__.py` | 包标记（空） |
| Create | `scripts/gate/violation.py` | `Severity` + `Violation` —— 唯一跨模块数据结构 |
| Create | `scripts/gate/context.py` | 仓库根定位、路径归类、gitignore 查询 |
| Create | `scripts/gate/runner.py` | 三种模式的编排：跑哪些 checker、喂什么内容 |
| Create | `scripts/gate/checkers/__init__.py` | 包标记（空） |
| Create | `scripts/gate/checkers/structure.py` | STR001–STR006 |
| Create | `scripts/gate/checkers/genericity.py` | GEN001–GEN004 |
| Create | `scripts/gate/checkers/registry.py` | REG001–REG003 |
| Create | `scripts/gate/checkers/evidence.py` | EVI001–EVI004 |
| Create | `scripts/gate/wordlist.txt` | GEN004 业务术语黑名单，默认仅注释 |
| Create | `scripts/gate/tests/*.py` | 每个 checker 一个测试文件 + runner + hook 契约 + baseline |
| Create | `rules/agent-behavior/evolution-gate.md` | 规则层：P0.8–P0.10 + Violation 码表 |
| Modify | `rules/agent-behavior/agent-behavior.md` | 末尾引出 evolution-gate.md |
| Modify | `CLAUDE.md` | 路由表新增一行 + 自我进化机制章节补闸门说明 |
| Modify | `AGENTS.md` / `GEMINI.md` | 自我进化章节加同一条引用 |
| Modify | `hooks/hooks.json` | 修 schema 与 matcher + 挂闸门 |
| Modify | `skills/{gen-page-test,locator-replacer,add-regression-point,architecture,case-round-trip}/SKILL.md` | 修 8 条死链 |
| Modify | `rules/agent-behavior/browser-tool-usage.md` | 补 5 条 ❌ 反例 |
| Delete | `zh/`、`en/` | 历史副本（末位任务，需用户二次确认） |

**任务顺序的硬约束**：Task 1、2 的存量修复必须早于 Task 9 的 baseline 测试，否则 baseline 无法断言零违规。

---

### Task 1: 修复 8 条死链

`skills/` 下 6 个 SKILL.md 共 8 处链接写作 `../../../docs/...`，跳出了仓库。这是从 `.claude/skills/` 迁到 `skills/` 时漏改的路径深度 —— 旧布局下 `../../../` 恰为仓库根，新布局下多跳一层。正确写法是 `../../docs/...`。

**Files:**
- Modify: `skills/gen-page-test/SKILL.md:29`
- Modify: `skills/locator-replacer/SKILL.md:177`
- Modify: `skills/add-regression-point/SKILL.md:73,77`
- Modify: `skills/architecture/SKILL.md:154,161`
- Modify: `skills/case-round-trip/SKILL.md:83`（同一行两处）

**Interfaces:**
- Consumes: 无
- Produces: 无代码接口。为 Task 9 的 baseline 消除 8 条 STR004 违规。

- [ ] **Step 1: 记录修复前的死链基数**

Run:
```bash
grep -rn "\.\./\.\./\.\./docs/" skills/ | wc -l
```
Expected: `8`

- [ ] **Step 2: 批量替换路径层级**

Run:
```bash
for f in skills/gen-page-test/SKILL.md skills/locator-replacer/SKILL.md \
         skills/add-regression-point/SKILL.md skills/architecture/SKILL.md \
         skills/case-round-trip/SKILL.md; do
  python3 - "$f" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text(encoding="utf-8").replace("../../../docs/", "../../docs/"), encoding="utf-8")
PY
done
```

- [ ] **Step 3: 验证全部死链已消除**

Run:
```bash
grep -rn "\.\./\.\./\.\./docs/" skills/ | wc -l
```
Expected: `0`

- [ ] **Step 4: 验证新路径真实可达**

Run:
```bash
python3 - <<'PY'
import re, pathlib
bad = []
for p in pathlib.Path("skills").rglob("*.md"):
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        for m in re.finditer(r'\[[^\]]*\]\(([^)]+)\)', line):
            t = m.group(1).split('#')[0].strip()
            if t and not t.startswith(('http://', 'https://', 'mailto:')) and not (p.parent / t).exists():
                bad.append(f"{p}:{i} -> {t}")
print("死链:", bad or "无")
PY
```
Expected: `死链: 无`

- [ ] **Step 5: 提议 commit（由用户执行）**

向用户提议：
```bash
git add skills/
git commit -m "fix(skills): 修正 8 条跳出仓库的 docs 相对链接"
```
执行者不得自行提交（Global Constraints）。

---

### Task 2: 为 browser-tool-usage.md 补 ❌ 反例

该文件有 5 处 ✅ 正例、0 处 ❌ 反例，违反「规则必含 ❌反例 + ✅正例」，是闸门 STR003 查出的真实存量违规。顺带修正 P0.4.3 的 ✅ 正例 —— 它示范了 `agent-browser open` 却没有紧跟 viewport 设置，与全局约定冲突。

**Files:**
- Modify: `rules/agent-behavior/browser-tool-usage.md`

**Interfaces:**
- Consumes: 无
- Produces: 无代码接口。为 Task 9 的 baseline 消除 1 条 STR003 违规。

- [ ] **Step 1: 确认修复前状态**

Run: `grep -c "❌" rules/agent-behavior/browser-tool-usage.md`
Expected: `0`

- [ ] **Step 2: 在 P0.4.1 的 ✅ 正例前插入 ❌ 反例**

在第 19 行 `✅ 正例：` 之前插入：

````markdown
❌ 反例：

```bash
agent-browser click @e27   # 没反应
agent-browser click @e27   # 再点一次 —— 仍然没反应
agent-browser click @e27   # 第三次 —— CDP 合成事件不会因为重试而生效，纯浪费 token
```

````

- [ ] **Step 3: 在 P0.4.2 的 ✅ 正例前插入 ❌ 反例**

在 `## P0.4.2 · agent-browser 触发新 tab 后必须手动切换` 小节的 `✅ 正例：` 之前插入：

````markdown
❌ 反例：

```bash
agent-browser click @e11
agent-browser snapshot -i -c   # 抓到的仍是旧 tab 的内容
# → 误判为"点击没生效"，转而去改定位符，排查方向从一开始就是错的
```

````

- [ ] **Step 4: 在 P0.4.2.1 的 ✅ 正例前插入 ❌ 反例**

在 `## P0.4.2.1 · Playwright MCP 跨子域 SSO 免登：必须等 networkidle 再跳转` 小节的 `✅ 正例：` 之前插入：

````markdown
❌ 反例：

```
browser_navigate → <BASE_URL>/entry?token=JWT
browser_navigate → <TARGET_SUBDOMAIN>/...   # SSO cookie 仍在异步写入 → 被重定向回登录页
```

````

- [ ] **Step 5: 在 P0.4.3 插入 ❌ 反例，并修正 ✅ 正例的 viewport**

在 `## P0.4.3 · 编写新用例前必须验证现有定位符` 小节的 `✅ 正例：` 之前插入：

````markdown
❌ 反例：

```python
# 直接照抄 PageObject 里的现有定位符写新用例，不开页面验证
COURSE_TAB = "text=课程"          # 页面早已改版，该文案不复存在
# → 新用例一跑就 TimeoutError，而问题根本不在新写的代码里
```

````

同时把该小节 ✅ 正例的代码块替换为：

```bash
agent-browser open <页面URL>
agent-browser set viewport 1024 768
agent-browser snapshot -s "<目标容器选择器>"
# 确认实际文本与代码中定位符一致，不一致则先修正再写用例
```

- [ ] **Step 6: 在 P0.4.4 的 ✅ 正例前插入 ❌ 反例**

在 `## P0.4.4 · 批量多视图采集用 eval 循环，不逐个手动交互` 小节的 `✅ 正例：` 之前插入：

````markdown
❌ 反例：

```bash
agent-browser click @e31 && agent-browser snapshot -i -c
agent-browser click @e32 && agent-browser snapshot -i -c
agent-browser click @e33 && agent-browser snapshot -i -c
# ... 14 个元素 = 28 条命令，token 消耗是 eval 循环的十几倍
```

````

- [ ] **Step 7: 验证 ❌ / ✅ 配平**

Run:
```bash
echo "❌=$(grep -c '❌' rules/agent-behavior/browser-tool-usage.md) ✅=$(grep -c '✅' rules/agent-behavior/browser-tool-usage.md)"
grep -n "set viewport" rules/agent-behavior/browser-tool-usage.md
```
Expected: `❌=5 ✅=5`，且 viewport 行存在。

- [ ] **Step 8: 提议 commit（由用户执行）**

```bash
git add rules/agent-behavior/browser-tool-usage.md
git commit -m "fix(rules): browser-tool-usage 补齐 5 条 ❌ 反例并修正 viewport 示例"
```

---

### Task 3: Violation 契约与 context 归类

闸门的地基。`Violation` 是唯一跨模块数据结构，`context` 负责「这个文件归谁管」。

**Files:**
- Create: `scripts/gate/__init__.py`（空文件）
- Create: `scripts/gate/violation.py`
- Create: `scripts/gate/context.py`
- Create: `scripts/gate/tests/__init__.py`（空文件）
- Test: `scripts/gate/tests/test_context.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `violation.Severity`：`IntEnum`，`WARN=1 < ASK=2 < BLOCK=3`
  - `violation.Violation(code, severity, path, line, message, fix)`：frozen dataclass，方法 `render() -> str`
  - `context.find_repo_root(start: pathlib.Path) -> pathlib.Path | None`
  - `context.relative_to_root(path, root) -> pathlib.PurePosixPath | None`
  - `context.classify(rel) -> str`，返回常量 `SKILL` / `RULE` / `DOC` / `ENTRY` / `MIRROR` / `IRRELEVANT`
  - `context.git_ignored(path_str: str, root_str: str) -> bool`

- [ ] **Step 1: 写失败测试**

创建 `scripts/gate/tests/test_context.py`：

```python
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from gate import context
from gate.violation import Severity, Violation


class TestClassify(unittest.TestCase):
    def _c(self, s):
        return context.classify(pathlib.PurePosixPath(s))

    def test_skill_md(self):
        self.assertEqual(self._c("skills/quick-debug/SKILL.md"), context.SKILL)

    def test_router_skill_is_skill(self):
        self.assertEqual(self._c("skills/SKILL.md"), context.SKILL)

    def test_rule_md(self):
        self.assertEqual(self._c("rules/playwright/locator-strategy.md"), context.RULE)

    def test_doc_md(self):
        self.assertEqual(self._c("docs/architecture.md"), context.DOC)

    def test_superpowers_is_irrelevant(self):
        # spec §6.1 豁免：spec 与 plan 是长篇流程文档，不受结构检查约束
        self.assertEqual(self._c("docs/superpowers/plans/x.md"), context.IRRELEVANT)

    def test_entry_files(self):
        self.assertEqual(self._c("CLAUDE.md"), context.ENTRY)
        self.assertEqual(self._c("AGENTS.md"), context.ENTRY)

    def test_mirror_dirs(self):
        self.assertEqual(self._c("zh/skills/quick-debug/SKILL.md"), context.MIRROR)
        self.assertEqual(self._c("en/rules/rules-index.md"), context.MIRROR)

    def test_source_code_irrelevant(self):
        self.assertEqual(self._c("pages/base_page.py"), context.IRRELEVANT)
        self.assertEqual(self._c("conftest.py"), context.IRRELEVANT)

    def test_none_is_irrelevant(self):
        self.assertEqual(context.classify(None), context.IRRELEVANT)


class TestViolation(unittest.TestCase):
    def test_severity_ordering(self):
        self.assertTrue(Severity.BLOCK > Severity.ASK > Severity.WARN)

    def test_render_with_line(self):
        v = Violation("STR001", Severity.BLOCK, "skills/a/SKILL.md", 3, "缺 name", "补上 name")
        out = v.render()
        self.assertIn("STR001", out)
        self.assertIn("skills/a/SKILL.md:3", out)
        self.assertIn("补上 name", out)

    def test_render_without_line(self):
        v = Violation("STR003", Severity.BLOCK, "rules/x.md", None, "缺反例", "补反例")
        self.assertIn("rules/x.md —", v.render())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'gate'`

- [ ] **Step 3: 创建包标记文件**

Run:
```bash
mkdir -p scripts/gate/checkers scripts/gate/tests
touch scripts/gate/__init__.py scripts/gate/checkers/__init__.py scripts/gate/tests/__init__.py
```

- [ ] **Step 4: 实现 `scripts/gate/violation.py`**

```python
"""Violation 契约 —— gate 包内唯一跨模块数据结构。"""
from __future__ import annotations

import enum
from dataclasses import dataclass


class Severity(enum.IntEnum):
    WARN = 1
    ASK = 2
    BLOCK = 3


@dataclass(frozen=True)
class Violation:
    code: str
    severity: Severity
    path: str
    line: "int | None"
    message: str
    fix: str

    def render(self) -> str:
        loc = f"{self.path}:{self.line}" if self.line else self.path
        return f"[{self.code}] {loc} — {self.message}\n  修法：{self.fix}"
```

- [ ] **Step 5: 实现 `scripts/gate/context.py`**

```python
"""路径归类、仓库根定位、gitignore 查询。"""
from __future__ import annotations

import functools
import pathlib
import subprocess

SKILL = "skill"
RULE = "rule"
DOC = "doc"
ENTRY = "entry"
MIRROR = "mirror"
IRRELEVANT = "irrelevant"

ENTRY_FILES = {"CLAUDE.md", "AGENTS.md", "GEMINI.md"}
MIRROR_ROOTS = ("zh", "en")
# spec §6.1 豁免：spec / plan 是长篇流程文档，不是 harness 知识
EXEMPT_PREFIXES = ("docs/superpowers/",)


def find_repo_root(start: pathlib.Path):
    start = pathlib.Path(start).resolve()
    for d in [start, *start.parents]:
        if (d / ".git").exists():
            return d
    return None


def relative_to_root(path, root):
    try:
        rel = pathlib.Path(path).resolve().relative_to(pathlib.Path(root).resolve())
    except (ValueError, OSError):
        return None
    return pathlib.PurePosixPath(rel.as_posix())


def classify(rel) -> str:
    if rel is None:
        return IRRELEVANT
    rel_s = str(rel)
    parts = rel.parts
    if not parts:
        return IRRELEVANT
    if parts[0] in MIRROR_ROOTS:
        return MIRROR
    if any(rel_s.startswith(p) for p in EXEMPT_PREFIXES):
        return IRRELEVANT
    if len(parts) == 1 and parts[0] in ENTRY_FILES:
        return ENTRY
    if rel.suffix != ".md":
        return IRRELEVANT
    if parts[0] == "skills":
        return SKILL
    if parts[0] == "rules":
        return RULE
    if parts[0] == "docs":
        return DOC
    return IRRELEVANT


@functools.lru_cache(maxsize=None)
def git_ignored(path_str: str, root_str: str) -> bool:
    """目标路径是否被 .gitignore 忽略。git 不可用时返回 False（fail-open）。"""
    try:
        r = subprocess.run(
            ["git", "-C", root_str, "check-ignore", "-q", path_str],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False
```

- [ ] **Step 6: 运行测试确认通过**

Run: `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: PASS，12 个测试全绿

- [ ] **Step 7: 提议 commit（由用户执行）**

```bash
git add scripts/gate/
git commit -m "feat(gate): 新增 Violation 契约与路径归类基础设施"
```

---

### Task 4: structure checker（STR001–STR006）

**Files:**
- Create: `scripts/gate/checkers/structure.py`
- Test: `scripts/gate/tests/test_structure.py`

**Interfaces:**
- Consumes: `violation.Severity`、`violation.Violation`、`context.git_ignored`
- Produces: `structure.check(rel: PurePosixPath, text: str, root: pathlib.Path) -> list[Violation]`

- [ ] **Step 1: 写失败测试**

创建 `scripts/gate/tests/test_structure.py`：

```python
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from gate.checkers import structure
from gate.violation import Severity

P = pathlib.PurePosixPath
GOOD_FM = "---\nname: quick-debug\ndescription: 排查测试失败\n---\n\n# 正文\n"


def codes(vs):
    return sorted(v.code for v in vs)


class TestSkillFrontmatter(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())

    def test_valid_skill_passes(self):
        vs = structure.check(P("skills/quick-debug/SKILL.md"), GOOD_FM, self.root)
        self.assertEqual(codes(vs), [])

    def test_missing_frontmatter(self):
        vs = structure.check(P("skills/quick-debug/SKILL.md"), "# 只有正文\n", self.root)
        self.assertIn("STR001", codes(vs))

    def test_missing_description(self):
        text = "---\nname: quick-debug\n---\n\n# 正文\n"
        vs = structure.check(P("skills/quick-debug/SKILL.md"), text, self.root)
        self.assertIn("STR001", codes(vs))

    def test_name_mismatch(self):
        text = "---\nname: wrong-name\ndescription: x\n---\n\n# 正文\n"
        vs = structure.check(P("skills/quick-debug/SKILL.md"), text, self.root)
        self.assertIn("STR002", codes(vs))

    def test_router_skill_exempt_from_name_check(self):
        # skills/SKILL.md 的 name 是 ui-automation-harness，目录名是 skills，唯一例外
        text = "---\nname: ui-automation-harness\ndescription: 路由入口\n---\n\n# 正文\n"
        vs = structure.check(P("skills/SKILL.md"), text, self.root)
        self.assertNotIn("STR002", codes(vs))


class TestRuleExamples(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())

    def test_rule_with_both_examples_passes(self):
        vs = structure.check(P("rules/x/y.md"), "❌ 反例\n✅ 正例\n", self.root)
        self.assertNotIn("STR003", codes(vs))

    def test_rule_missing_counter_example(self):
        vs = structure.check(P("rules/x/y.md"), "✅ 正例\n", self.root)
        self.assertIn("STR003", codes(vs))

    def test_index_file_exempt(self):
        vs = structure.check(P("rules/rules-index.md"), "只有链接\n", self.root)
        self.assertNotIn("STR003", codes(vs))

    def test_overview_file_exempt(self):
        vs = structure.check(P("rules/playwright/playwright-overview.md"), "只有链接\n", self.root)
        self.assertNotIn("STR003", codes(vs))


class TestLinks(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / "docs").mkdir()
        (self.root / "docs" / "real.md").write_text("x", encoding="utf-8")
        (self.root / "skills" / "s").mkdir(parents=True)

    def test_reachable_link_passes(self):
        text = "见 [doc](../../docs/real.md)\n"
        vs = structure.check(P("skills/s/SKILL.md"), text, self.root)
        self.assertNotIn("STR004", codes(vs))

    def test_dead_link_blocks(self):
        text = "见 [doc](../../../docs/real.md)\n"
        vs = structure.check(P("skills/s/SKILL.md"), text, self.root)
        self.assertIn("STR004", codes(vs))

    def test_external_url_ignored(self):
        text = "见 [x](https://example.com/a)\n"
        vs = structure.check(P("skills/s/SKILL.md"), text, self.root)
        self.assertNotIn("STR004", codes(vs))


class TestSize(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())

    def test_warn_over_300(self):
        vs = structure.check(P("rules/x/y.md"), "❌\n✅\n" + "行\n" * 320, self.root)
        self.assertIn("STR005", codes(vs))
        self.assertNotIn("STR006", codes(vs))

    def test_block_over_500(self):
        vs = structure.check(P("rules/x/y.md"), "❌\n✅\n" + "行\n" * 520, self.root)
        self.assertIn("STR006", codes(vs))

    def test_superpowers_exempt(self):
        vs = structure.check(P("docs/superpowers/plans/p.md"), "行\n" * 800, self.root)
        self.assertEqual(codes(vs), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m unittest scripts.gate.tests.test_structure -v` 或 `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: FAIL，`ImportError: cannot import name 'structure'`

- [ ] **Step 3: 实现 `scripts/gate/checkers/structure.py`**

```python
"""维度② 结构合规 —— STR001–STR006。"""
from __future__ import annotations

import re

from ..context import EXEMPT_PREFIXES, git_ignored
from ..violation import Severity, Violation

MAX_LINES_WARN = 300
MAX_LINES_BLOCK = 500

ROUTER_SKILL = "skills/SKILL.md"
INDEX_SUFFIXES = ("-index.md", "-overview.md")

_FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _frontmatter(text):
    m = _FM_RE.match(text)
    return m.group(1) if m else None


def _fm_field(fm, key):
    prefix = key + ":"
    for line in fm.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return None


def check(rel, text, root):
    rel_s = str(rel)
    if any(rel_s.startswith(p) for p in EXEMPT_PREFIXES):
        return []

    out = []
    top = rel.parts[0]

    if top == "skills" and rel.name == "SKILL.md":
        out.extend(_check_skill_frontmatter(rel, rel_s, text))

    if top == "rules" and not rel_s.endswith(INDEX_SUFFIXES):
        if "❌" not in text or "✅" not in text:
            out.append(Violation(
                "STR003", Severity.BLOCK, rel_s, None,
                "规则文件必须同时含 ❌ 反例与 ✅ 正例",
                "为每条规则补一组 ❌ 反例 / ✅ 正例代码块",
            ))

    out.extend(_check_links(rel_s, text, root))
    out.extend(_check_size(rel_s, text))
    return out


def _check_skill_frontmatter(rel, rel_s, text):
    fm = _frontmatter(text)
    if fm is None:
        return [Violation(
            "STR001", Severity.BLOCK, rel_s, 1,
            "SKILL.md 缺少 YAML frontmatter",
            "在文件开头加 ---\\nname: <目录名>\\ndescription: <触发词>\\n---",
        )]
    name = _fm_field(fm, "name")
    if name is None or _fm_field(fm, "description") is None:
        return [Violation(
            "STR001", Severity.BLOCK, rel_s, 1,
            "frontmatter 缺少 name 或 description 字段",
            "补齐 name 与 description 两个字段",
        )]
    if rel_s == ROUTER_SKILL:
        return []
    expect = rel.parent.name
    if name != expect:
        return [Violation(
            "STR002", Severity.BLOCK, rel_s, 1,
            f"frontmatter name='{name}' 与目录名 '{expect}' 不一致",
            f"把 name 改为 {expect}",
        )]
    return []


def _check_links(rel_s, text, root):
    out = []
    base = (root / rel_s).parent
    root_s = str(root)
    for i, line in enumerate(text.splitlines(), 1):
        for m in _LINK_RE.finditer(line):
            target = m.group(1).split("#")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = base / target
            if resolved.exists():
                continue
            if git_ignored(str(resolved), root_s):
                continue
            out.append(Violation(
                "STR004", Severity.BLOCK, rel_s, i,
                f"链接指向不存在的路径：{target}",
                "修正相对路径层级，或补上缺失的目标文件",
            ))
    return out


def _check_size(rel_s, text):
    n = len(text.splitlines())
    if n > MAX_LINES_BLOCK:
        return [Violation(
            "STR006", Severity.BLOCK, rel_s, None,
            f"文件 {n} 行，超过上限 {MAX_LINES_BLOCK}",
            "拆分为多个按主题聚焦的文件，并在索引文件中互相引用",
        )]
    if n > MAX_LINES_WARN:
        return [Violation(
            "STR005", Severity.WARN, rel_s, None,
            f"文件 {n} 行，超过建议值 {MAX_LINES_WARN}",
            "考虑拆分；单文件过长会挤占 agent 上下文",
        )]
    return []
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: PASS

- [ ] **Step 5: 提议 commit（由用户执行）**

```bash
git add scripts/gate/checkers/structure.py scripts/gate/tests/test_structure.py
git commit -m "feat(gate): 实现 structure checker（STR001-STR006）"
```

---

### Task 5: genericity checker（GEN001–GEN004）

本任务风险最高的是 GEN003 的误报边界：现有库里哈希类名出现 8 次，**全部是反例教学**。判定必须能区分「使用哈希类名」与「讲解哈希类名不能用」。

**Files:**
- Create: `scripts/gate/checkers/genericity.py`
- Create: `scripts/gate/wordlist.txt`
- Test: `scripts/gate/tests/test_genericity.py`

**Interfaces:**
- Consumes: `violation.Severity`、`violation.Violation`
- Produces: `genericity.check(rel: PurePosixPath, text: str, root: pathlib.Path | None = None) -> list[Violation]`

- [ ] **Step 1: 写失败测试**

创建 `scripts/gate/tests/test_genericity.py`：

```python
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from gate.checkers import genericity

P = pathlib.PurePosixPath
SKILL = P("skills/demo/SKILL.md")


def codes(vs):
    return sorted(v.code for v in vs)


class TestScope(unittest.TestCase):
    def test_only_applies_to_skills(self):
        vs = genericity.check(P("rules/x/y.md"), "见 https://intranet.corp.example/a\n")
        self.assertEqual(codes(vs), [])


class TestUrl(unittest.TestCase):
    def test_concrete_url_blocks(self):
        vs = genericity.check(SKILL, "打开 https://portal.acme-internal.net/home\n")
        self.assertIn("GEN001", codes(vs))

    def test_example_com_whitelisted(self):
        vs = genericity.check(SKILL, "打开 https://example.com/xxx\n")
        self.assertNotIn("GEN001", codes(vs))

    def test_ellipsis_placeholder_whitelisted(self):
        # 现有 gen-page-test/SKILL.md:11 的真实写法，末尾紧跟全角括号
        vs = genericity.check(SKILL, "给定页面（https://...）生成页面对象和测试\n")
        self.assertNotIn("GEN001", codes(vs))

    def test_doc_domains_whitelisted(self):
        vs = genericity.check(SKILL, "见 https://playwright.dev/docs/locators\n")
        self.assertNotIn("GEN001", codes(vs))


class TestAbsPath(unittest.TestCase):
    def test_mac_user_path_blocks(self):
        vs = genericity.check(SKILL, "打开 /Users/alice/repo/pages/x.py\n")
        self.assertIn("GEN002", codes(vs))

    def test_relative_path_passes(self):
        vs = genericity.check(SKILL, "打开 pages/base_page.py\n")
        self.assertNotIn("GEN002", codes(vs))


class TestHashClass(unittest.TestCase):
    def test_real_assignment_blocks(self):
        vs = genericity.check(SKILL, 'LOGIN_BTN = "css=.sc-bdVaJa"\n')
        self.assertIn("GEN003", codes(vs))

    def test_bad_comment_exempt(self):
        # locator-replacer/SKILL.md:71 的真实写法
        vs = genericity.check(SKILL, '# BAD: "css=.sc-bdVaJa.bVjGWg"         (styled-components 哈希)\n')
        self.assertNotIn("GEN003", codes(vs))

    def test_table_row_exempt(self):
        # locator-replacer/SKILL.md:84 的真实写法
        vs = genericity.check(SKILL, "| Emotion | 前缀 css- | `.css-1a2b3c` |\n")
        self.assertNotIn("GEN003", codes(vs))

    def test_checklist_exempt(self):
        # locator-replacer/SKILL.md:186 的真实写法
        vs = genericity.check(SKILL, "- [ ] 没有使用哈希类名（`sc-xxx`, `css-xxx`, `_module_xxx`）\n")
        self.assertNotIn("GEN003", codes(vs))

    def test_cross_mark_line_exempt(self):
        vs = genericity.check(SKILL, '❌ 反例：LOGIN = "css=.css-1a2b3c"\n')
        self.assertNotIn("GEN003", codes(vs))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: FAIL，`ImportError: cannot import name 'genericity'`

- [ ] **Step 3: 创建 `scripts/gate/wordlist.txt`**

```text
# GEN004 业务术语黑名单 —— 每行一个词，# 开头为注释。
# 默认为空。使用者按自己项目填入不应出现在 skills/ 正文中的专有业务术语，
# 例如产品代号、内部系统名、角色称谓。命中只给 WARN，不阻断。
```

- [ ] **Step 4: 实现 `scripts/gate/checkers/genericity.py`**

```python
"""维度③ 通用化检测 —— GEN001–GEN004，仅作用于 skills/**。"""
from __future__ import annotations

import functools
import pathlib
import re

from ..violation import Severity, Violation

# 全角标点需排除，否则中文正文里的 URL 会一路吞到句末
_URL_RE = re.compile(r"https?://[^\s)\]\"'`，。）、；：]+")
_ABS_PATH_RE = re.compile(r"(?:/Users/|/Applications/|/home/|[A-Za-z]:\\)[^\s)\]\"'`，。）]*")
_HASH_CLASS_RE = re.compile(
    r"\.(?:sc-[A-Za-z]{4,}|css-[0-9a-z]{5,}|[A-Za-z]*_[A-Za-z]+_[0-9a-z]{3,})"
)

_URL_WHITELIST = (
    "example.com", "example.org", "example.net",
    "github.com/DanielSuo117/velocitai",
    "docs.claude.com", "code.claude.com",
    "playwright.dev", "docs.pytest.org",
)
_URL_PLACEHOLDER_PREFIXES = ("https://...", "http://...")

_EXEMPT_MARKERS = ("BAD", "❌", "禁止")
_WORDLIST = pathlib.Path(__file__).resolve().parent.parent / "wordlist.txt"


def _is_teaching_line(line: str) -> bool:
    """反例教学语境豁免 —— 注释 / 表格 / 清单 / 显式反例标记。"""
    s = line.lstrip()
    if s.startswith(("#", "|", "- [ ]", "- [x]")):
        return True
    return any(mark in line for mark in _EXEMPT_MARKERS)


@functools.lru_cache(maxsize=1)
def _wordlist():
    try:
        lines = _WORDLIST.read_text(encoding="utf-8").splitlines()
    except Exception:
        return ()
    return tuple(w for w in (l.strip() for l in lines) if w and not w.startswith("#"))


def check(rel, text, root=None):
    if rel.parts[0] != "skills":
        return []
    rel_s = str(rel)
    out = []
    words = _wordlist()

    for i, line in enumerate(text.splitlines(), 1):
        for m in _URL_RE.finditer(line):
            url = m.group(0)
            if url.startswith(_URL_PLACEHOLDER_PREFIXES):
                continue
            if any(w in url for w in _URL_WHITELIST):
                continue
            out.append(Violation(
                "GEN001", Severity.BLOCK, rel_s, i,
                f"skill 正文出现具体 URL：{url}",
                "抽象为占位符（如 <目标页面URL>）；项目级 URL 放 docs/ 或 config/",
            ))

        for m in _ABS_PATH_RE.finditer(line):
            out.append(Violation(
                "GEN002", Severity.BLOCK, rel_s, i,
                f"skill 正文出现本地绝对路径：{m.group(0)}",
                "改为相对仓库根的路径，或抽象为占位符",
            ))

        if not _is_teaching_line(line):
            m = _HASH_CLASS_RE.search(line)
            if m:
                out.append(Violation(
                    "GEN003", Severity.BLOCK, rel_s, i,
                    f"skill 正文出现哈希类名：{m.group(0)}",
                    "哈希类名每次构建都会变；升级到 P0 role 或 P1 text 定位",
                ))
            for w in words:
                if w in line:
                    out.append(Violation(
                        "GEN004", Severity.WARN, rel_s, i,
                        f"skill 正文出现业务术语「{w}」",
                        "skill 须保持项目无关；业务术语抽象为占位符或移入 docs/",
                    ))
    return out
```

- [ ] **Step 5: 运行测试确认通过**

Run: `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: PASS

- [ ] **Step 6: 用真实文件验证零误报**

Run:
```bash
python3 - <<'PY'
import pathlib, sys
sys.path.insert(0, "scripts")
from gate.checkers import genericity
root = pathlib.Path(".")
hits = []
for p in sorted(root.glob("skills/**/*.md")):
    rel = pathlib.PurePosixPath(p.as_posix())
    hits += genericity.check(rel, p.read_text(encoding="utf-8"))
print("命中:", [v.render() for v in hits] or "无")
PY
```
Expected: `命中: 无` —— 现有 8 处哈希类名与 3 处 URL 全部落在豁免语境。

- [ ] **Step 7: 提议 commit（由用户执行）**

```bash
git add scripts/gate/checkers/genericity.py scripts/gate/wordlist.txt scripts/gate/tests/test_genericity.py
git commit -m "feat(gate): 实现 genericity checker（GEN001-GEN004）"
```

---

### Task 6: registry checker（REG001–REG003）

**Files:**
- Create: `scripts/gate/checkers/registry.py`
- Test: `scripts/gate/tests/test_registry.py`

**Interfaces:**
- Consumes: `violation.Severity`、`violation.Violation`、`context.git_ignored`
- Produces:
  - `registry.check_write(rel: PurePosixPath) -> list[Violation]`（仅 REG003 镜像守卫）
  - `registry.check_repo(root: pathlib.Path) -> list[Violation]`（REG001 + REG002，仅 commit / audit）

- [ ] **Step 1: 写失败测试**

创建 `scripts/gate/tests/test_registry.py`：

```python
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from gate.checkers import registry

P = pathlib.PurePosixPath


def codes(vs):
    return sorted(v.code for v in vs)


class TestMirrorGuard(unittest.TestCase):
    def test_zh_write_blocked(self):
        self.assertIn("REG003", codes(registry.check_write(P("zh/skills/a/SKILL.md"))))

    def test_en_write_blocked(self):
        self.assertIn("REG003", codes(registry.check_write(P("en/rules/x.md"))))

    def test_root_write_allowed(self):
        self.assertEqual(codes(registry.check_write(P("skills/a/SKILL.md"))), [])


class TestRepoChecks(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / "skills" / "alpha").mkdir(parents=True)
        (self.root / "skills" / "alpha" / "SKILL.md").write_text("x", encoding="utf-8")
        (self.root / "docs").mkdir()
        (self.root / "docs" / "real.md").write_text("x", encoding="utf-8")

    def _write_claude(self, body):
        (self.root / "CLAUDE.md").write_text(body, encoding="utf-8")

    def test_registered_skill_passes(self):
        self._write_claude("| 建 | [alpha](./skills/alpha/) |\n")
        self.assertNotIn("REG001", codes(registry.check_repo(self.root)))

    def test_unregistered_skill_blocks(self):
        self._write_claude("# 没有路由表\n")
        self.assertIn("REG001", codes(registry.check_repo(self.root)))

    def test_dead_route_link_blocks(self):
        self._write_claude("| 建 | [alpha](./skills/alpha/) |\n| 文档 | [d](./docs/missing.md) |\n")
        self.assertIn("REG002", codes(registry.check_repo(self.root)))

    def test_live_route_link_passes(self):
        self._write_claude("| 建 | [alpha](./skills/alpha/) |\n| 文档 | [d](./docs/real.md) |\n")
        self.assertNotIn("REG002", codes(registry.check_repo(self.root)))

    def test_missing_claude_md_is_noop(self):
        self.assertEqual(codes(registry.check_repo(self.root)), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: FAIL，`ImportError: cannot import name 'registry'`

- [ ] **Step 3: 实现 `scripts/gate/checkers/registry.py`**

```python
"""维度④ 注册闭环 + 镜像弃用守卫 —— REG001–REG003。"""
from __future__ import annotations

import re

from ..context import MIRROR_ROOTS, git_ignored
from ..violation import Severity, Violation

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def check_write(rel):
    """写入时机：仅镜像弃用守卫。"""
    if rel is not None and rel.parts and rel.parts[0] in MIRROR_ROOTS:
        return [Violation(
            "REG003", Severity.BLOCK, str(rel), None,
            f"{rel.parts[0]}/ 是 i18n 合并前的历史副本，已弃用，不得新增内容",
            "改为写入仓库根的对应路径；该目录待删除",
        )]
    return []


def check_repo(root):
    """commit / audit 时机：全局注册闭环。"""
    claude_md = root / "CLAUDE.md"
    if not claude_md.exists():
        return []
    try:
        text = claude_md.read_text(encoding="utf-8")
    except Exception:
        return []

    out = []
    for skill_md in sorted(root.glob("skills/*/SKILL.md")):
        name = skill_md.parent.name
        if f"./skills/{name}/" not in text:
            out.append(Violation(
                "REG001", Severity.BLOCK, f"skills/{name}/SKILL.md", None,
                f"skill '{name}' 未在 CLAUDE.md 路由表注册",
                f"在 CLAUDE.md 路由表新增一行，链接指向 ./skills/{name}/",
            ))

    root_s = str(root)
    for i, line in enumerate(text.splitlines(), 1):
        for m in _LINK_RE.finditer(line):
            target = m.group(1).split("#")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = root / target
            if resolved.exists() or git_ignored(str(resolved), root_s):
                continue
            out.append(Violation(
                "REG002", Severity.BLOCK, "CLAUDE.md", i,
                f"路由表链接指向不存在的路径：{target}",
                "修正链接，或补上缺失的目标文件",
            ))
    return out
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: PASS

- [ ] **Step 5: 对真实仓库验证 REG001/REG002 零违规**

Run:
```bash
python3 - <<'PY'
import pathlib, sys
sys.path.insert(0, "scripts")
from gate.checkers import registry
vs = registry.check_repo(pathlib.Path("."))
print("命中:", [v.render() for v in vs] or "无")
PY
```
Expected: `命中: 无` —— 12 个 skill 全部已注册；`CLAUDE.local.md` 被 gitignore 豁免。

- [ ] **Step 6: 提议 commit（由用户执行）**

```bash
git add scripts/gate/checkers/registry.py scripts/gate/tests/test_registry.py
git commit -m "feat(gate): 实现 registry checker（REG001-REG003）"
```

---

### Task 7: evidence checker（EVI001–EVI004）

**Files:**
- Create: `scripts/gate/checkers/evidence.py`
- Test: `scripts/gate/tests/test_evidence.py`

**Interfaces:**
- Consumes: `violation.Severity`、`violation.Violation`
- Produces:
  - `evidence.PROPOSAL_CHECKLIST: str`（EVI001 的 ASK 理由文案，gate_cli 直接透传给用户）
  - `evidence.check(rel, text, root, is_new: bool = False) -> list[Violation]`

- [ ] **Step 1: 写失败测试**

创建 `scripts/gate/tests/test_evidence.py`：

```python
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from gate.checkers import evidence
from gate.violation import Severity

P = pathlib.PurePosixPath


def codes(vs):
    return sorted(v.code for v in vs)


class TestNewFileAsk(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())

    def test_new_skill_asks(self):
        vs = evidence.check(P("skills/new/SKILL.md"), "正文", self.root, is_new=True)
        self.assertIn("EVI001", codes(vs))
        ask = [v for v in vs if v.code == "EVI001"][0]
        self.assertEqual(ask.severity, Severity.ASK)

    def test_new_rule_asks(self):
        vs = evidence.check(P("rules/x/new.md"), "❌\n✅\n", self.root, is_new=True)
        self.assertIn("EVI001", codes(vs))

    def test_existing_file_does_not_ask(self):
        vs = evidence.check(P("rules/x/new.md"), "❌\n✅\n", self.root, is_new=False)
        self.assertNotIn("EVI001", codes(vs))

    def test_new_doc_does_not_ask(self):
        # docs/ 是项目事实清单，追加事实不需确认
        vs = evidence.check(P("docs/pages-catalog.md"), "正文", self.root, is_new=True)
        self.assertNotIn("EVI001", codes(vs))


class TestTriggerEvidence(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / "rules").mkdir()

    def test_clause_without_any_trigger_blocks(self):
        text = "## 🔴 P0.1 · 某规则\n\n规则内容\n"
        vs = evidence.check(P("rules/x.md"), text, self.root)
        self.assertIn("EVI002", codes(vs))

    def test_file_level_trigger_satisfies_block(self):
        # skill-authoring.md 的真实形态：文件级触发行覆盖三个条款
        text = "**触发**：新建 / 修改 skills/**\n\n## P0.5 · A\n\n## P0.6 · B\n"
        vs = evidence.check(P("rules/x.md"), text, self.root)
        self.assertNotIn("EVI002", codes(vs))

    def test_clause_level_missing_trigger_warns(self):
        text = "**触发**：文件级\n\n## P0.5 · A\n\n内容\n"
        vs = evidence.check(P("rules/x.md"), text, self.root)
        warns = [v for v in vs if v.code == "EVI003"]
        self.assertEqual(len(warns), 1)
        self.assertEqual(warns[0].severity, Severity.WARN)

    def test_clause_with_own_trigger_no_warn(self):
        text = "## 🔴 P0.1 · A\n\n**触发**：某情况\n\n内容\n"
        vs = evidence.check(P("rules/x.md"), text, self.root)
        self.assertNotIn("EVI003", codes(vs))

    def test_non_clause_file_not_checked(self):
        text = "## 普通小节\n\n内容\n"
        vs = evidence.check(P("rules/x.md"), text, self.root)
        self.assertNotIn("EVI002", codes(vs))


class TestDuplicateHeading(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / "rules").mkdir()
        (self.root / "rules" / "existing.md").write_text(
            "## 状态类 selector 必须配 text 锁定\n", encoding="utf-8"
        )

    def test_near_duplicate_warns(self):
        text = "## 状态类 selector 必须配 text 锁定\n"
        vs = evidence.check(P("rules/new.md"), text, self.root)
        self.assertIn("EVI004", codes(vs))

    def test_distinct_heading_passes(self):
        text = "## 浏览器 context 复用策略\n"
        vs = evidence.check(P("rules/new.md"), text, self.root)
        self.assertNotIn("EVI004", codes(vs))

    def test_self_not_compared(self):
        text = "## 状态类 selector 必须配 text 锁定\n"
        vs = evidence.check(P("rules/existing.md"), text, self.root)
        self.assertNotIn("EVI004", codes(vs))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: FAIL，`ImportError: cannot import name 'evidence'`

- [ ] **Step 3: 实现 `scripts/gate/checkers/evidence.py`**

```python
"""维度① 证据门槛与去重 —— EVI001–EVI004。"""
from __future__ import annotations

import re

from ..violation import Severity, Violation

_CLAUSE_RE = re.compile(r"^##\s+.*\bP\d")
_HEADING_RE = re.compile(r"^##\s+(.*)$")
_TRIGGER = "**触发**"
_NOISE_RE = re.compile(r"[·:：、，。()（）\[\]`*#\-—\s]|🔴|🟡|🟢|⚠️|P[\d.]+")

DUP_THRESHOLD = 0.6

PROPOSAL_CHECKLIST = (
    "在 skills/ 或 rules/ 下新建文件需先提案。请先向用户说明：\n"
    "  1. 触发条件 —— 什么情况下会再次遇到\n"
    "  2. 失败现象 —— 这次实际踩了什么坑\n"
    "  3. 拟写入位置 —— 为什么是新建文件而非并入已有文件\n"
    "  4. 检索结果 —— 与哪条既有规则相关，为何不能合并"
)


def check(rel, text, root, is_new: bool = False):
    rel_s = str(rel)
    top = rel.parts[0]
    out = []

    if is_new and top in ("skills", "rules"):
        out.append(Violation(
            "EVI001", Severity.ASK, rel_s, None,
            "在 skills/ 或 rules/ 下新建文件，需用户确认",
            PROPOSAL_CHECKLIST,
        ))

    if top != "rules":
        return out

    lines = text.splitlines()
    clause_idx = [i for i, l in enumerate(lines) if _CLAUSE_RE.match(l)]

    if clause_idx and _TRIGGER not in text:
        out.append(Violation(
            "EVI002", Severity.BLOCK, rel_s, clause_idx[0] + 1,
            "含 P 级条款但全文没有 **触发**： 行 —— 没有触发条件的规则等于没有证据",
            "为规则补 **触发**：<什么情况下适用>；文件级触发行亦可覆盖全文",
        ))

    for pos, start in enumerate(clause_idx):
        end = clause_idx[pos + 1] if pos + 1 < len(clause_idx) else len(lines)
        if not any(l.startswith(_TRIGGER) for l in lines[start:end]):
            title = lines[start].lstrip("# ").strip()
            out.append(Violation(
                "EVI003", Severity.WARN, rel_s, start + 1,
                f"条款「{title}」内部没有 **触发**： 行",
                "补条款级 **触发**：行；若已有文件级触发行覆盖，可忽略",
            ))

    out.extend(_dup_headings(rel_s, lines, root))
    return out


def _bigrams(title: str):
    """中文无空格分词，用字符二元组做相似度，避免整句比对失效。"""
    s = _NOISE_RE.sub("", title)
    if len(s) < 2:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _dup_headings(rel_s, lines, root):
    existing = []
    try:
        candidates = sorted(root.glob("rules/**/*.md"))
    except Exception:
        return []
    for p in candidates:
        try:
            rel_other = p.relative_to(root).as_posix()
        except ValueError:
            continue
        if rel_other == rel_s:
            continue
        try:
            body = p.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, l in enumerate(body.splitlines(), 1):
            m = _HEADING_RE.match(l)
            if m:
                existing.append((_bigrams(m.group(1)), f"{rel_other}:{i}", m.group(1)))

    out = []
    for i, l in enumerate(lines, 1):
        m = _HEADING_RE.match(l)
        if not m:
            continue
        a = _bigrams(m.group(1))
        if not a:
            continue
        for b, loc, raw in existing:
            if not b:
                continue
            j = len(a & b) / len(a | b)
            if j >= DUP_THRESHOLD:
                out.append(Violation(
                    "EVI004", Severity.WARN, rel_s, i,
                    f"标题与 {loc}「{raw}」重叠 {j:.0%}，疑似重复",
                    "先检索既有规则；重复内容应合并进原文件，而非新增条款",
                ))
                break
    return out
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: PASS

- [ ] **Step 5: 提议 commit（由用户执行）**

```bash
git add scripts/gate/checkers/evidence.py scripts/gate/tests/test_evidence.py
git commit -m "feat(gate): 实现 evidence checker（EVI001-EVI004）"
```

---

### Task 8: runner 编排与 gate_cli 入口

把四个 checker 接成三种运行模式，并实现 hook 协议输出。本任务包含两个最易出错的实现契约：**Edit 场景需重建全文**、**fail-open 不得逃逸**。

**Files:**
- Create: `scripts/gate/runner.py`
- Create: `scripts/gate_cli.py`
- Test: `scripts/gate/tests/test_runner.py`
- Test: `scripts/gate/tests/test_hook_contract.py`

**Interfaces:**
- Consumes: 全部四个 checker、`context.*`、`violation.Severity`
- Produces:
  - `runner.run_write(payload: dict) -> list[Violation]`
  - `runner.run_commit(root) -> list[Violation]`
  - `runner.run_audit(root) -> list[Violation]`
  - `gate_cli.py --mode {write,commit,audit}`，退出码 0 或 2

- [ ] **Step 1: 写 runner 失败测试**

创建 `scripts/gate/tests/test_runner.py`：

```python
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from gate import runner


def codes(vs):
    return sorted(v.code for v in vs)


class TestRunWrite(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / ".git").mkdir()
        (self.root / "skills" / "demo").mkdir(parents=True)
        (self.root / "rules").mkdir()

    def _payload(self, tool, path, **ti):
        ti["file_path"] = str(self.root / path)
        return {"tool_name": tool, "tool_input": ti, "cwd": str(self.root)}

    def test_irrelevant_file_skipped(self):
        p = self._payload("Write", "pages/base_page.py", content="x = 1")
        self.assertEqual(codes(runner.run_write(p)), [])

    def test_non_edit_tool_skipped(self):
        p = self._payload("Bash", "skills/demo/SKILL.md", content="x")
        self.assertEqual(codes(runner.run_write(p)), [])

    def test_mirror_write_blocked(self):
        p = self._payload("Write", "zh/skills/demo/SKILL.md", content="x")
        self.assertIn("REG003", codes(runner.run_write(p)))

    def test_new_skill_triggers_ask(self):
        p = self._payload("Write", "skills/demo/SKILL.md",
                          content="---\nname: demo\ndescription: d\n---\n")
        self.assertIn("EVI001", codes(runner.run_write(p)))

    def test_existing_skill_no_ask(self):
        target = self.root / "skills" / "demo" / "SKILL.md"
        target.write_text("---\nname: demo\ndescription: d\n---\n", encoding="utf-8")
        p = self._payload("Write", "skills/demo/SKILL.md",
                          content="---\nname: demo\ndescription: d\n---\n新增一行\n")
        self.assertNotIn("EVI001", codes(runner.run_write(p)))

    def test_edit_rebuilds_full_text(self):
        target = self.root / "rules" / "r.md"
        target.write_text("❌ 反例\n✅ 正例\n旧内容\n", encoding="utf-8")
        p = self._payload("Edit", "rules/r.md", old_string="旧内容", new_string="新内容")
        # 重建后仍含 ❌ 与 ✅ → 不应报 STR003
        self.assertNotIn("STR003", codes(runner.run_write(p)))

    def test_edit_removing_examples_blocks(self):
        target = self.root / "rules" / "r.md"
        target.write_text("❌ 反例\n✅ 正例\n", encoding="utf-8")
        p = self._payload("Edit", "rules/r.md", old_string="❌ 反例\n", new_string="")
        self.assertIn("STR003", codes(runner.run_write(p)))

    def test_edit_with_unmatched_old_string_fails_open(self):
        target = self.root / "rules" / "r.md"
        target.write_text("✅ 只有正例\n", encoding="utf-8")
        p = self._payload("Edit", "rules/r.md", old_string="不存在的串", new_string="x")
        self.assertEqual(codes(runner.run_write(p)), [])

    def test_malformed_payload_fails_open(self):
        self.assertEqual(codes(runner.run_write({})), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: FAIL，`ImportError: cannot import name 'runner'`

- [ ] **Step 3: 实现 `scripts/gate/runner.py`**

```python
"""三种运行模式的编排。"""
from __future__ import annotations

import os
import pathlib
import subprocess

from . import context
from .checkers import evidence, genericity, registry, structure


def _content_checks(rel, text, root, is_new=False):
    out = []
    out.extend(structure.check(rel, text, root))
    out.extend(genericity.check(rel, text, root))
    out.extend(evidence.check(rel, text, root, is_new=is_new))
    return out


def run_write(payload):
    tool = (payload or {}).get("tool_name")
    if tool not in ("Write", "Edit"):
        return []
    ti = payload.get("tool_input") or {}
    fp = ti.get("file_path")
    if not fp:
        return []

    root = context.find_repo_root(pathlib.Path(payload.get("cwd") or os.getcwd()))
    if root is None:
        return []
    rel = context.relative_to_root(fp, root)
    kind = context.classify(rel)

    if kind == context.MIRROR:
        return registry.check_write(rel)
    if kind not in (context.SKILL, context.RULE, context.DOC):
        return []

    disk = pathlib.Path(fp)
    if tool == "Write":
        text = ti.get("content")
        if text is None:
            return []
        return _content_checks(rel, text, root, is_new=not disk.exists())

    # Edit：hook 只给 old_string / new_string，须读盘重建全文
    if not disk.exists():
        return []
    try:
        cur = disk.read_text(encoding="utf-8")
    except Exception:
        return []
    old, new = ti.get("old_string"), ti.get("new_string")
    if old is None or new is None or old not in cur:
        return []  # fail-open：匹配不上就不猜
    return _content_checks(rel, cur.replace(old, new, 1), root, is_new=False)


def _staged(root):
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return []
    if r.returncode != 0:
        return []
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def run_commit(root):
    if root is None:
        return []
    names = _staged(root)
    if not names:
        return []

    out = []
    for n in names:
        rel = pathlib.PurePosixPath(n)
        kind = context.classify(rel)
        if kind == context.MIRROR:
            out.extend(registry.check_write(rel))
            continue
        if kind not in (context.SKILL, context.RULE, context.DOC):
            continue
        p = root / n
        if not p.exists():
            continue
        try:
            out.extend(_content_checks(rel, p.read_text(encoding="utf-8"), root))
        except Exception:
            continue

    if any(n.startswith("skills/") or n == "CLAUDE.md" for n in names):
        out.extend(registry.check_repo(root))
    return out


def run_audit(root):
    if root is None:
        return []
    out = []
    seen = set()
    for pattern in ("skills/**/*.md", "rules/**/*.md", "docs/*.md"):
        for p in sorted(root.glob(pattern)):
            rel = pathlib.PurePosixPath(p.relative_to(root).as_posix())
            if str(rel) in seen:
                continue
            seen.add(str(rel))
            if context.classify(rel) not in (context.SKILL, context.RULE, context.DOC):
                continue
            try:
                out.extend(_content_checks(rel, p.read_text(encoding="utf-8"), root))
            except Exception:
                continue
    out.extend(registry.check_repo(root))
    return out
```

- [ ] **Step 4: 运行 runner 测试确认通过**

Run: `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: PASS

- [ ] **Step 5: 写 hook 契约失败测试**

创建 `scripts/gate/tests/test_hook_contract.py`：

```python
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

CLI = pathlib.Path(__file__).resolve().parents[2] / "gate_cli.py"


def run_cli(mode, payload):
    return subprocess.run(
        [sys.executable, str(CLI), "--mode", mode],
        input=json.dumps(payload), capture_output=True, text=True, timeout=30,
    )


class TestHookContract(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / ".git").mkdir()
        (self.root / "skills" / "demo").mkdir(parents=True)
        (self.root / "rules").mkdir()

    def _payload(self, tool, path, **ti):
        ti["file_path"] = str(self.root / path)
        return {"tool_name": tool, "tool_input": ti, "cwd": str(self.root)}

    def test_clean_write_exits_zero_silently(self):
        p = self._payload("Write", "docs/architecture.md", content="# 架构\n")
        (self.root / "docs").mkdir(exist_ok=True)
        r = run_cli("write", p)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_block_exits_two_with_deny(self):
        target = self.root / "skills" / "demo" / "SKILL.md"
        target.write_text("---\nname: demo\ndescription: d\n---\n", encoding="utf-8")
        p = self._payload("Write", "skills/demo/SKILL.md",
                          content='---\nname: wrong\ndescription: d\n---\n')
        r = run_cli("write", p)
        self.assertEqual(r.returncode, 2)
        out = json.loads(r.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("STR002", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_new_file_exits_zero_with_ask(self):
        p = self._payload("Write", "skills/demo/SKILL.md",
                          content="---\nname: demo\ndescription: d\n---\n")
        r = run_cli("write", p)
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")
        self.assertIn("触发条件", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_garbage_stdin_fails_open(self):
        r = subprocess.run(
            [sys.executable, str(CLI), "--mode", "write"],
            input="not json at all", capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: 运行测试确认失败**

Run: `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: FAIL，`gate_cli.py` 不存在

- [ ] **Step 7: 实现 `scripts/gate_cli.py`**

```python
#!/usr/bin/env python3
"""VelocitAI 落库校验闸门 —— 唯一入口。

用法：
    gate_cli.py --mode write     # PreToolUse(Write|Edit)，从 stdin 读 hook JSON
    gate_cli.py --mode commit    # PreToolUse(Bash git commit)，校验暂存区
    gate_cli.py --mode audit     # 全仓库扫描，供测试与 commit 模式内部使用

退出码：0 = 放行（可能带 ask 决策）；2 = 拦截。
任何异常一律 fail-open 返回 0。
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gate import context, runner            # noqa: E402
from gate.violation import Severity         # noqa: E402


def _root():
    return context.find_repo_root(pathlib.Path(os.getcwd()))


def _emit(violations) -> int:
    if not violations:
        return 0
    top = max(v.severity for v in violations)

    if top == Severity.BLOCK:
        body = "\n".join(v.render() for v in violations if v.severity == Severity.BLOCK)
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "落库校验闸门拦截：\n" + body,
        }}, ensure_ascii=False))
        return 2

    if top == Severity.ASK:
        body = "\n".join(v.render() for v in violations if v.severity == Severity.ASK)
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": body,
        }}, ensure_ascii=False))
        return 0

    print("落库校验提示：\n" + "\n".join(v.render() for v in violations), file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("write", "commit", "audit"), required=True)
    args = ap.parse_args()

    if args.mode == "write":
        payload = json.load(sys.stdin)
        return _emit(runner.run_write(payload))

    if args.mode == "commit":
        try:
            json.load(sys.stdin)
        except Exception:
            pass
        return _emit(runner.run_commit(_root()))

    return _emit(runner.run_audit(_root()))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # fail-open：宁可漏判，绝不阻塞
        print(f"[gate] 校验器异常，已放行：{exc}", file=sys.stderr)
        sys.exit(0)
```

- [ ] **Step 8: 运行全部测试确认通过**

Run: `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: PASS，全部测试绿

- [ ] **Step 9: 提议 commit（由用户执行）**

```bash
git add scripts/gate/runner.py scripts/gate_cli.py scripts/gate/tests/test_runner.py scripts/gate/tests/test_hook_contract.py
git commit -m "feat(gate): 实现 runner 编排与 gate_cli hook 协议入口"
```

---

### Task 9: 零误报回归基线

本计划最有价值的一个测试。它把设计阶段三轮实测得出的每一条豁免规则，固化成可执行断言：任何人改动 checker 正则引入误报，这里立刻红。

**前置条件：Task 1 与 Task 2 的存量修复必须已完成**，否则基线无法断言零违规。

**Files:**
- Test: `scripts/gate/tests/test_baseline.py`

**Interfaces:**
- Consumes: `runner.run_audit`、`violation.Severity`
- Produces: 无

- [ ] **Step 1: 确认前置存量修复已完成**

Run:
```bash
echo "死链: $(grep -rc '\.\./\.\./\.\./docs/' skills/ 2>/dev/null | awk -F: '{s+=$2} END {print s+0}')"
echo "browser-tool-usage ❌: $(grep -c '❌' rules/agent-behavior/browser-tool-usage.md)"
```
Expected: `死链: 0`、`browser-tool-usage ❌: 5`

- [ ] **Step 2: 写基线测试**

创建 `scripts/gate/tests/test_baseline.py`：

```python
"""零误报回归基线。

设计阶段对现有 harness 全量实测得出的豁免规则，在此固化为可执行断言：
  - skills/SKILL.md 的 name 与目录名不符（路由 skill，STR002 豁免）
  - rules-index.md / playwright-overview.md 无正反例（索引文件，STR003 豁免）
  - locator-replacer 中 8 处哈希类名全为反例教学（GEN003 豁免）
  - skill-authoring.md 用文件级触发行覆盖 3 个条款（EVI002 文件级判定）
  - CLAUDE.md → CLAUDE.local.md 为 gitignore 的可选文件（STR004/REG002 豁免）
  - docs/superpowers/** 为长篇流程文档（全量 STR 豁免）

任何 checker 改动导致本仓库出现 BLOCK，即为引入了误报。
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from gate import runner
from gate.violation import Severity

REPO = pathlib.Path(__file__).resolve().parents[3]


class TestBaseline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.violations = runner.run_audit(REPO)

    def test_no_block_violations(self):
        blocks = [v for v in self.violations if v.severity == Severity.BLOCK]
        self.assertEqual(
            blocks, [],
            "现有 harness 出现 BLOCK 违规，说明 checker 引入了误报：\n"
            + "\n".join(v.render() for v in blocks),
        )

    def test_no_ask_violations_in_audit(self):
        # audit 模式不判定新建，不应产生 ASK
        asks = [v for v in self.violations if v.severity == Severity.ASK]
        self.assertEqual(asks, [], "audit 模式不应产生 ASK")

    def test_audit_actually_scanned_files(self):
        # 防止 glob 写错导致"零违规"其实是"零扫描"
        self.assertTrue((REPO / "skills" / "quick-debug" / "SKILL.md").exists())
        self.assertGreaterEqual(len(list(REPO.glob("rules/**/*.md"))), 14)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 运行基线测试**

Run: `python3 -m unittest scripts.gate.tests.test_baseline -v` 或 `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: PASS

若 `test_no_block_violations` 失败，失败信息会逐条列出误报的码与位置。逐条对照 spec §6 的豁免规则修正 checker，**不得**通过放宽断言让测试变绿。

- [ ] **Step 4: 人工查看 WARN 清单**

Run:
```bash
python3 scripts/gate_cli.py --mode audit 2>&1 >/dev/null | head -40
```
Expected: 输出若干 WARN。预期包含 `skill-authoring.md` 的 3 条 EVI003（条款级缺触发行，已知且可接受）。确认没有异常的 WARN 涌现。

- [ ] **Step 5: 提议 commit（由用户执行）**

```bash
git add scripts/gate/tests/test_baseline.py
git commit -m "test(gate): 新增零误报回归基线，固化全部豁免规则"
```

---

### Task 10: 修复 hooks.json 并接入闸门

`hooks/hooks.json` 当前有两处偏离官方 plugin hooks 规范，导致插件用户装上后现有两个 hook 很可能从未生效。不修则新闸门会以同样方式失效。

**Files:**
- Modify: `hooks/hooks.json`

**Interfaces:**
- Consumes: `scripts/gate_cli.py` 的 `--mode write` / `--mode commit`
- Produces: 无代码接口

- [ ] **Step 1: 记录修复前的错误形态**

Run: `python3 -c "import json;d=json.load(open('hooks/hooks.json'));print(type(d['hooks']).__name__)"`
Expected: `list` —— 规范要求是 `dict`（按事件名分键）

- [ ] **Step 2: 用规范形态整体替换 `hooks/hooks.json`**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/gate_cli.py\" --mode write",
            "timeout": 10
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(git commit *)",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/gate_cli.py\" --mode commit",
            "timeout": 20
          },
          {
            "type": "command",
            "if": "Bash(git commit *)",
            "command": "code-review-graph build",
            "timeout": 30
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "code-review-graph status",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

三处改动：顶层 `hooks` 由数组改为按事件名分键的对象；`"matcher": "Bash(git commit *)"` 拆为 `"matcher": "Bash"` + handler 上的 `"if"`；新增闸门的两条接线。

- [ ] **Step 3: 验证 JSON 结构正确**

Run:
```bash
python3 - <<'PY'
import json
d = json.load(open("hooks/hooks.json"))
assert isinstance(d["hooks"], dict), "顶层 hooks 必须是对象"
pre = d["hooks"]["PreToolUse"]
assert {m["matcher"] for m in pre} == {"Write|Edit", "Bash"}, "matcher 集合不符"
cmds = [h["command"] for m in pre for h in m["hooks"]]
assert any("--mode write" in c for c in cmds), "缺 write 模式接线"
assert any("--mode commit" in c for c in cmds), "缺 commit 模式接线"
assert any("code-review-graph build" in c for c in cmds), "丢失原有 build hook"
print("hooks.json 结构校验通过")
PY
```
Expected: `hooks.json 结构校验通过`

- [ ] **Step 4: 同步 `.claude/settings.json` 的 matcher 修复**

把 `.claude/settings.json` 中 `hooks.PreToolUse` 下 `"matcher": "Bash(git commit *)"` 的那一项改为：

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "if": "Bash(git commit *)",
      "command": "code-review-graph build",
      "timeout": 30
    }
  ]
}
```

- [ ] **Step 5: 验证 settings.json 仍可解析**

Run: `python3 -c "import json; json.load(open('.claude/settings.json')); print('ok')"`
Expected: `ok`

- [ ] **Step 6: 端到端手工验证**

在 Claude Code 中依次尝试（每步观察实际行为）：
1. 编辑 `pages/base_page.py` → 预期：静默放行，无任何闸门输出
2. 新建 `skills/tmp-probe/SKILL.md` → 预期：弹出授权询问，理由含「触发条件 / 失败现象 / 拟写入位置 / 检索结果」四项
3. 把某个 SKILL.md 的 frontmatter `name` 改成错的 → 预期：被拦截，理由含 `STR002` 与具体修法
4. 验证完成后删除 `skills/tmp-probe/`

- [ ] **Step 7: 提议 commit（由用户执行）**

```bash
git add hooks/hooks.json .claude/settings.json
git commit -m "fix(hooks): 修正 plugin hooks schema 与 matcher，接入落库校验闸门"
```

---

### Task 11: 规则层与入口注册

闸门的脚本只覆盖 Claude Code。规则层是 Copilot / Gemini 唯一能读到的约束，也是整套机制的事实源。

**Files:**
- Create: `rules/agent-behavior/evolution-gate.md`
- Modify: `rules/agent-behavior/agent-behavior.md`（末尾）
- Modify: `CLAUDE.md`（路由表 + 自我进化机制章节）
- Modify: `AGENTS.md`（自我进化机制章节）
- Modify: `GEMINI.md`（自我进化机制章节）

**Interfaces:**
- Consumes: spec §6 的全部违规码
- Produces: 无代码接口

- [ ] **Step 1: 创建 `rules/agent-behavior/evolution-gate.md`**

```markdown
---
paths:
  - "skills/**"
  - "rules/**"
  - "docs/**"
---

# 落库校验规则（P0.8–P0.10）

**触发**：准备把经验 / 规则 / 项目事实写入 `skills/` / `rules/` / `docs/` 时。

自我进化机制写入的内容会被**每一个新会话加载为高优先级上下文**。垃圾数据在这套架构里不是静态污染，而是会自我强化的负反馈 —— 写错一次，之后每次编码都被它带偏。本规则是落库前的闸门。

---

## P0.8 · 沉淀前必须先检索去重

**触发**：准备新增规则条款或新建 skill 时。

**规则**：先检索 `rules/` 与 `skills/` 中的既有内容。已有同主题条款的，必须合并进原文件，禁止另起炉灶。

❌ 反例：遇到定位符超时问题，直接新建 `rules/playwright/timeout-new.md`，而 `timeout-and-wait.md` 已经在讲同一件事 —— 两份规则从此各说各话，agent 读到哪份全凭运气。

✅ 正例：先 grep「超时」，发现 `timeout-and-wait.md` 已覆盖，把新踩的坑作为一个 ❌/✅ 例子追加进该文件对应条款。

---

## P0.9 · 沉淀必须带触发条件与失败现象

**触发**：写入任何规则条款时。

**规则**：每条规则必须写明 `**触发**：<什么情况下适用>`，并附真实踩坑的失败现象。没有触发条件的规则等于没有证据，禁止落库。推测、一次性结论、通用常识一律不写。

❌ 反例：

```markdown
## P1.1 · 定位符要写得稳定一些

尽量使用语义化的定位方式。
```

既没有触发条件，也没有失败现象，更没有可执行的判定标准 —— agent 读了不知道何时该适用。

✅ 正例：

```markdown
## P1.1 · text= 是子串匹配，有包含关系时用精确匹配

**触发**：定位符文案是另一个元素文案的子串（如「添加」vs「批量添加」）。

**失败现象**：`.first` 命中了「批量添加」，测试不报错但操作了错误的按钮。

❌ `ADD_BTN = "text=添加"`
✅ `ADD_BTN = 'text="添加"'`
```

---

## P0.10 · 新建 skill / rule 必须先提案

**触发**：要在 `skills/` 或 `rules/` 下新建文件（而非在已有文件中追加）时。

**规则**：先向用户提案，说明四项：触发条件、失败现象、拟写入位置（为何是新建而非并入已有文件）、检索结果（与哪条既有规则相关）。获确认后才写。在已有文件中追加 ❌/✅ 例子、修正笔误、更新 `docs/` 事实清单，不受此限。

❌ 反例：排查完一个 bug，直接 Write 一个 `skills/new-debug-trick/SKILL.md`，用户毫不知情，路由表也没登记 —— 成为一个谁都不会去读的孤儿文件。

✅ 正例：向用户说明「这次踩的坑是 X，触发条件是 Y，既有的 quick-debug 没覆盖分支 Z，建议新建还是并入 quick-debug？」，由用户决定。

---

## 违规码速查

收到闸门拦截时，按码对照修改。

| 码 | 含义 | 修法 |
|---|---|---|
| STR001 | SKILL.md 缺 frontmatter 或缺 name/description | 补齐 `name` 与 `description` 两个字段 |
| STR002 | frontmatter `name` 与目录名不一致 | 把 `name` 改为目录名 |
| STR003 | 规则文件缺 ❌ 反例或 ✅ 正例 | 为每条规则补一组 ❌/✅ 代码块 |
| STR004 | Markdown 链接指向不存在的路径 | 修正相对路径层级，或补上目标文件 |
| STR005 | 文件超过 300 行 | 建议拆分（仅提示，不阻断） |
| STR006 | 文件超过 500 行 | 拆分为多个按主题聚焦的文件 |
| GEN001 | skill 正文出现具体 URL | 抽象为占位符；项目级 URL 放 `docs/` 或 `config/` |
| GEN002 | skill 正文出现本地绝对路径 | 改为相对仓库根的路径 |
| GEN003 | skill 正文出现哈希类名 | 升级到 P0 role 或 P1 text 定位 |
| GEN004 | skill 正文出现业务术语黑名单词 | 抽象为占位符或移入 `docs/` |
| REG001 | skill 未在 CLAUDE.md 路由表注册 | 在路由表新增一行 |
| REG002 | 路由表链接指向不存在的路径 | 修正链接或补上目标文件 |
| REG003 | 写入已弃用的 `zh/` 或 `en/` 目录 | 改为写入仓库根的对应路径 |
| EVI001 | 在 skills/ 或 rules/ 下新建文件 | 按 P0.10 先提案（需用户确认，非错误） |
| EVI002 | 含 P 级条款但全文无 `**触发**：` 行 | 按 P0.9 补触发条件 |
| EVI003 | 条款内部无 `**触发**：` 行 | 补条款级触发行（仅提示） |
| EVI004 | 标题与既有条款高度重叠 | 按 P0.8 合并进原文件 |

---

## 闸门失效时

校验脚本遵循 fail-open：异常一律放行。所以**闸门没拦住不等于内容合格** —— P0.8/P0.9/P0.10 是必须自觉遵守的规则，脚本只是兜底。
```

- [ ] **Step 2: 在 `agent-behavior.md` 末尾引出新规则**

在文件末尾（`P0.5–P0.7（Skill 编写规则）→ ...` 那一行之后）追加：

```markdown

P0.8–P0.10（落库校验规则）→ 仅在写入 `skills/**` / `rules/**` / `docs/**` 时加载 → [evolution-gate.md](./evolution-gate.md)
```

- [ ] **Step 3: 在 `CLAUDE.md` 路由表新增一行**

在路由表中 `| **编码规范**（命名/基类/用例） | [coding-conventions](...) |` 这一行之前插入：

```markdown
| **落库校验** / 沉淀闸门 | [evolution-gate](./rules/agent-behavior/evolution-gate.md) |
```

- [ ] **Step 4: 修改 `CLAUDE.md` 的自我进化机制章节**

把该章节末尾的执行行：

```markdown
执行：Edit 最小增量写入；回复末尾声明 `📝 已沉淀至 <file>：<摘要>`。
```

替换为：

```markdown
执行：先过[落库闸门](./rules/agent-behavior/evolution-gate.md)（检索去重 → 带触发条件与失败现象 → 新建文件先提案）；再 Edit 最小增量写入；回复末尾声明 `📝 已沉淀至 <file>：<摘要>`。
```

- [ ] **Step 5: 在 `AGENTS.md` 自我进化机制章节补引用**

在该章节的三条映射之后追加：

```markdown

写入前必须先过落库闸门：检索去重 → 每条规则带触发条件与失败现象 → 新建 skill/rule 先向用户提案。完整条款见 `rules/agent-behavior/evolution-gate.md`。
```

- [ ] **Step 6: 在 `GEMINI.md` 自我进化章节补同样的引用**

Run: `grep -n "自我进化" GEMINI.md`

在其自我进化章节末尾追加与 Step 5 相同的段落（按 GEMINI.md 既有措辞风格微调即可，内容三点不得减少）。

- [ ] **Step 7: 验证新规则文件自身能通过闸门**

Run:
```bash
python3 - <<'PY'
import pathlib, sys
sys.path.insert(0, "scripts")
from gate import runner
from gate.violation import Severity
vs = runner.run_audit(pathlib.Path("."))
blocks = [v for v in vs if v.severity == Severity.BLOCK]
print("BLOCK:", [v.render() for v in blocks] or "无")
PY
```
Expected: `BLOCK: 无` —— `evolution-gate.md` 含 ❌/✅（过 STR003）、含 `**触发**：`（过 EVI002）、链接可达（过 STR004）。

- [ ] **Step 8: 重跑全部测试**

Run: `python3 -m unittest discover -s scripts/gate/tests -v`
Expected: PASS，含 baseline

- [ ] **Step 9: 提议 commit（由用户执行）**

```bash
git add rules/agent-behavior/evolution-gate.md rules/agent-behavior/agent-behavior.md CLAUDE.md AGENTS.md GEMINI.md
git commit -m "feat(rules): 新增落库校验规则 P0.8-P0.10 并在各入口注册"
```

---

### Task 12: 删除历史镜像 `zh/` 与 `en/`

`zh/` 与 `en/` 是 i18n 合并前的历史副本。根 `index.html` 已完成单文件双语合并（274 处 `data-lang` 标记），两个镜像下的 `index.html` 均为 0 处标记的合并前版本。保留它们会持续制造三份不同步。

**⚠️ 本任务不可逆，涉及 88 个已入库文件。执行前必须向用户单独确认，获明确同意后才动手。**

**Files:**
- Delete: `zh/`（44 个已入库文件）
- Delete: `en/`（44 个已入库文件）

**Interfaces:**
- Consumes: 无
- Produces: 无

- [ ] **Step 1: 向用户单独确认**

向用户说明：将删除 `zh/` 与 `en/` 两个目录共 88 个已入库文件，操作不可逆（可通过 git 历史恢复）。**必须获得明确同意才进入下一步。** 用户不同意则跳过本任务，并把 REG003 镜像守卫保留为长期约束。

- [ ] **Step 2: 确认无外部引用指向镜像目录**

Run:
```bash
grep -rn "](\./zh/\|](\./en/\|(/zh/\|(/en/\|zh/index.html\|en/index.html" \
  --include="*.md" --include="*.html" --include="*.json" . \
  | grep -v "^./zh/" | grep -v "^./en/" | grep -v "^./.git/"
```
Expected: 无输出。若有输出，先修正这些引用再删除。

- [ ] **Step 3: 删除目录**

Run:
```bash
git rm -r --quiet zh en
```

- [ ] **Step 4: 验证删除结果**

Run:
```bash
ls -d zh en 2>&1 | head -2
git status --short | head -5
```
Expected: `ls` 报 No such file or directory；`git status` 显示大量 `D` 条目。

- [ ] **Step 5: 确认闸门与测试仍全绿**

Run:
```bash
python3 -m unittest discover -s scripts/gate/tests -v
python3 - <<'PY'
import pathlib, sys
sys.path.insert(0, "scripts")
from gate import runner
from gate.violation import Severity
vs = runner.run_audit(pathlib.Path("."))
print("BLOCK:", [v.render() for v in vs if v.severity == Severity.BLOCK] or "无")
PY
```
Expected: 全部测试 PASS；`BLOCK: 无`

- [ ] **Step 6: 提议 commit（由用户执行）**

```bash
git commit -m "chore: 删除 i18n 合并前的 zh/ 与 en/ 历史镜像"
```

---

## Self-Review Checklist

- [x] **Spec coverage**：spec §3 三层 → Task 3–8（校验层）、Task 10（接线层）、Task 11（规则层）；§5 Violation 契约 → Task 3；§6.1–6.4 四个 checker → Task 4–7；§7 三种模式 → Task 8；§8 hook 接线 → Task 10；§9.1 Edit 重建全文 → Task 8 Step 3 + `test_edit_rebuilds_full_text`；§9.2 新建判定 → Task 8 Step 3 + `test_new_skill_triggers_ask`；§9.3 commit 不追究存量 → Task 8 `run_commit` 只读暂存区；§9.4 fail-open → Task 8 Step 7 顶层捕获 + `test_garbage_stdin_fails_open`；§10 规则层与入口 → Task 11；§11 测试与验收 → Task 9；§12.1 → Task 2；§12.2 → Task 10；§12.3 → Task 1；§12.4 → Task 12。无遗漏。
- [x] **Placeholder scan**：无 TBD / TODO / "类似 Task N" / "补充适当的错误处理"。每个代码步骤都给了可直接落地的完整代码，每个验证步骤都给了可直接运行的命令与预期输出。
- [x] **Type consistency**：`Violation(code, severity, path, line, message, fix)` 六个字段在 Task 3 定义后，Task 4–7 全部按此构造；`check(rel, text, root)` 签名在 structure / genericity 一致，evidence 多一个 `is_new` 关键字参数且在 Task 7 Interfaces 与 Task 8 `runner._content_checks` 调用处一致；registry 拆为 `check_write(rel)` 与 `check_repo(root)` 两个签名，Task 6 定义、Task 8 调用一致；`context` 的六个常量与四个函数在 Task 3 定义，Task 4/6/8 引用一致。
- [x] **依赖顺序**：Task 1、2（存量修复）早于 Task 9（baseline）；Task 3（契约）早于 Task 4–8；Task 8（cli）早于 Task 10（hook 接线）；Task 12 置于末位且带二次确认。
- [x] **约束一致性**：全部 Commit 步骤均写明「由用户执行」，符合项目 P0.3；全部代码仅用 Python 3 标准库；全部测试为 stdlib unittest。

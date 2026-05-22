# Harness 同步与通用化实施计划

> **代理工作者注意：** 必须使用子技能：优先使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务执行本计划。步骤使用复选框（`- [ ]`）语法跟踪进度。

**目标：** 将 zhs-web-regression-hub 项目中 `.claude/` harness 的最新改动同步到 velocitai 通用模板，修复残留问题，补全 settings.json 权限缺口。

**架构说明：** velocitai 已完成大部分通用化工作（28 个文件中 27 个已处理）。本次工作聚焦 4 个问题：report-strategy.md 的 P1/P2 章节同步滞后、gen-page-test SKILL.md 的残留类名、settings.json 的通用权限缺失。所有改动均在 velocitai 仓库内完成，不修改 zhs 源项目。

**技术栈：** Markdown、JSON（`.claude/settings.json`）

---

## 文件结构

| 操作 | 文件路径 | 职责 |
|------|---------|------|
| 修改 | `.claude/rules/report-strategy/report-strategy.md` | 同步 P1 自动轮转 + 新增 P2 运行日志（通用化版本） |
| 修改 | `.claude/skills/gen-page-test/SKILL.md` | 修复 Step 4 第 74 行残留的 `TestStudentHome` 和路径重复 |
| 修改 | `.claude/settings.json` | 补全通用权限条目 |

---

### 任务 1：同步 report-strategy.md 的 P1 自动轮转章节

**文件：**
- 修改：`.claude/rules/report-strategy/report-strategy.md:1-5`（frontmatter paths）
- 修改：`.claude/rules/report-strategy/report-strategy.md:83-89`（P1 章节）

- [ ] **步骤 1：更新 frontmatter，添加 `utils/log_config.py` 路径声明**

将第 1-5 行：

```yaml
---
paths:
  - "conftest.py"
  - "utils/report_generator.py"
---
```

替换为：

```yaml
---
paths:
  - "conftest.py"
  - "utils/report_generator.py"
  - "utils/log_config.py"
---
```

- [ ] **步骤 2：将 P1 章节从"手动清理"升级为"自动轮转"**

将第 83-89 行（P1 章节）：

```markdown
## 🟡 P1 · 报告文件清理

**触发**：验证测试或调试后产生了临时报告文件。

**规则**：手动验证（故意失败测试）产生的报告文件必须在验证完成后清理，不入库。`reports/` 目录已在 `.gitignore` 中，但本地积累过多仍会占磁盘。
```

替换为：

```markdown
## 🟡 P1 · 报告文件自动轮转

**触发**：`utils/report_generator.py` 生成报告后执行清理逻辑。

**规则**：`reports/html/` 下最多保留 **10** 份 `report_*.html`，超出时按文件名排序删除最旧报告。

**实现位置**：`utils/report_generator.py` 中独立的清理方法。

```python
def _cleanup_old_reports(output_dir: Path, max_count: int = 10):
    reports = sorted(output_dir.glob("report_*.html"))
    while len(reports) > max_count:
        reports.pop(0).unlink()
```

**调用时机**：在 `generate_html_report()` 成功写入新报告后调用，与报告生成解耦（清理失败不影响报告写入）。

❌ 反例：在报告生成前清理（可能删掉未读的报告）

✅ 正例：先生成新报告 → 再清理超出上限的旧报告
```

- [ ] **步骤 3：在 P1 后新增 P2 运行日志章节**

在 P1 章节和"扩展点"章节之间插入：

```markdown
---

## 🟡 P2 · 运行日志记录

**触发**：每次 pytest session 启动时。

**规则**：每次运行生成独立日志文件 `logs/test_run_<timestamp>.log`，同时维护 `logs/latest.log` 软链接指向最新日志。最多保留 **100** 份日志文件。

**实现位置**：`utils/log_config.py` 中的 `setup_logging()` 函数。

```python
def setup_logging(log_dir: str = "logs", max_files: int = 100) -> str:
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"test_run_{timestamp}.log"

    # 配置 logging handler
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    logging.root.addHandler(handler)

    # 软链接
    latest = log_path / "latest.log"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(log_file.name)

    # 轮转
    logs = sorted(log_path.glob("test_run_*.log"))
    while len(logs) > max_files:
        logs.pop(0).unlink()

    return str(log_file)
```

**调用时机**：在 `conftest.py` 的 `pytest_configure` hook 中调用。

```python
def pytest_configure(config):
    from utils.log_config import setup_logging
    setup_logging()
```

❌ 反例：在 `pytest_sessionstart` 中调用（时机过晚，fixture 级日志丢失）

✅ 正例：在 `pytest_configure` 中调用（pytest 最早可用 hook）
```

- [ ] **步骤 4：验证文件格式正确**

运行：`head -120 /Applications/AgenticAI_2603/github/velocitai/.claude/rules/report-strategy/report-strategy.md`
预期：frontmatter 含 3 个 paths、P0/P1/P2 三个章节完整、扩展点章节保留。

- [ ] **步骤 5：提交**

```bash
git add .claude/rules/report-strategy/report-strategy.md
git commit -m "sync: 同步 report-strategy P1 自动轮转 + P2 运行日志章节"
```

---

### 任务 2：修复 gen-page-test SKILL.md 的残留问题

**文件：**
- 修改：`.claude/skills/gen-page-test/SKILL.md:74`

- [ ] **步骤 1：修复 Step 4 第 74 行的残留类名和路径重复**

将第 74 行：

```markdown
目标文件：对应角色 `tests/<role>/test_<role>_flow.py`（继承 `<Role>BaseTest`） `tests/<role>/test_<role>_flow.py` 的 `TestStudentHome` 类。
```

替换为：

```markdown
目标文件：对应角色 `tests/<role>/test_<role>_flow.py`（继承 `<Role>BaseTest`）中的 `Test<Role>Flow` 类。
```

- [ ] **步骤 2：验证修复正确**

运行：`grep -n "TestStudentHome\|TestStudent" /Applications/AgenticAI_2603/github/velocitai/.claude/skills/gen-page-test/SKILL.md`
预期：无匹配结果（零输出）。

- [ ] **步骤 3：提交**

```bash
git add .claude/skills/gen-page-test/SKILL.md
git commit -m "fix: 移除 gen-page-test 中残留的 TestStudentHome 类名"
```

---

### 任务 3：补全 settings.json 通用权限条目

**文件：**
- 修改：`.claude/settings.json:3-29`（allow 列表）

- [ ] **步骤 1：在 allow 列表中追加通用权限条目**

在 `"Bash(agent-browser install *)"` 之后、`]` 之前追加以下条目：

```json
      "Bash(agent-browser --cdp * open *)",
      "Bash(agent-browser --cdp * snapshot *)",
      "Bash(agent-browser --cdp * eval *)",
      "Bash(agent-browser --cdp * click *)",
      "Bash(agent-browser --cdp * tab *)",
      "Bash(agent-browser --cdp * batch *)",
      "Bash(agent-browser snapshot *)",
      "Bash(agent-browser eval *)",
      "Bash(agent-browser click *)",
      "Bash(agent-browser tab *)",
      "Bash(agent-browser open *)",
      "Bash(agent-browser batch *)",
      "Bash([ -f *)",
      "Bash([ -d *)",
      "Skill(add-regression-point)",
      "Skill(add-regression-point:*)"
```

- [ ] **步骤 2：验证 JSON 格式正确**

运行：`python3 -c "import json; json.load(open('/Applications/AgenticAI_2603/github/velocitai/.claude/settings.json'))"`
预期：无输出（解析成功）。

- [ ] **步骤 3：验证新增条目存在**

运行：`grep -c "agent-browser" /Applications/AgenticAI_2603/github/velocitai/.claude/settings.json`
预期：数字 >= 14（原有 4 + 新增 10）。

- [ ] **步骤 4：提交**

```bash
git add .claude/settings.json
git commit -m "feat: 补全 settings.json 中 agent-browser 和 skill 通用权限"
```

---

## 自检清单

- [x] **规格覆盖：** 3 个发现的问题（report-strategy 同步滞后 × 2、gen-page-test 残留、settings.json 权限缺失）全部有对应任务
- [x] **占位符扫描：** 所有任务的代码块和命令均为完整内容，无 TBD/TODO
- [x] **类型一致性：** 文件路径、方法名在各任务之间一致（`_cleanup_old_reports`、`setup_logging`、`Test<Role>Flow`）
- [x] **通用化验证：** 所有新增内容不含任何项目特定标识（智慧树/zhs/teacher/student/zhihuishu/具体 URL/本地路径）

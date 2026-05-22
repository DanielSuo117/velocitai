---
paths:
  - "conftest.py"
  - "utils/report_generator.py"
  - "utils/log_config.py"
---

# 测试报告生成策略

适用于：`conftest.py` 中 `pytest_sessionfinish` 报告生成逻辑、`utils/report_generator.py` 报告工具。

---

## 🔴 P0 · 仅失败时生成 HTML 报告

**触发**：pytest session 结束、报告生成逻辑执行时。

**规则**：全部用例通过时跳过 HTML 报告生成，仅当存在失败（failed / broken / teardown error）用例时才生成报告。避免每次跑测试都堆积无意义的"全绿"报告文件。

**实现模式**：模块级标记变量 + hook 检测 + sessionfinish 条件判断。

### 标记变量设置

`_has_failures` 必须在 `report.failed` 为 True 的**任意阶段**（setup / call / teardown）设置，不能仅限 call/setup。截图逻辑和标记逻辑必须解耦。

❌ 反例：标记与截图耦合，遗漏 teardown 失败

```python
def pytest_runtest_makereport(item, call):
    global _has_failures
    outcome = yield
    report = outcome.get_result()
    if report.when in ("call", "setup") and report.failed:
        _has_failures = True          # teardown 失败不会设置标记
        try:
            ...screenshot...
        except Exception:
            pass
```

✅ 正例：标记与截图解耦，覆盖全阶段

```python
def pytest_runtest_makereport(item, call):
    global _has_failures
    outcome = yield
    report = outcome.get_result()
    if report.failed:                 # 任意阶段失败都标记
        _has_failures = True
    if report.when in ("call", "setup") and report.failed:
        try:
            ...screenshot...          # 截图仅 call/setup
        except Exception:
            pass
```

### sessionfinish 条件判断

报告生成的条件判断必须放在域名打印之后、报告生成之前。域名统计信息无论通过与否都应输出（用于排查网络问题）。

❌ 反例：无条件生成报告

```python
def pytest_sessionfinish(session, exitstatus):
    ...域名打印...
    report_path = generate_html_report(results_dir, output_dir, env)  # 全绿也生成
```

✅ 正例：仅失败时生成

```python
def pytest_sessionfinish(session, exitstatus):
    ...域名打印...

    if not _has_failures:
        print("\n✅ 所有用例通过，跳过 HTML 报告生成")
        return

    ...报告生成逻辑...
```

---

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

---

## 扩展点（备忘）

如未来需要更精细的控制（如仅 broken 时生成、按模块分别决策），可考虑：
- 使用 `session.testsfailed`（pytest 内置属性）替代手动标记
- 在 `generate_html_report` 内部根据 stats 决定是否写文件

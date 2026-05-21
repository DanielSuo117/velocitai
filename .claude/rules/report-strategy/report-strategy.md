---
paths:
  - "conftest.py"
  - "utils/report_generator.py"
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

## 🟡 P1 · 报告文件清理

**触发**：验证测试或调试后产生了临时报告文件。

**规则**：手动验证（故意失败测试）产生的报告文件必须在验证完成后清理，不入库。`reports/` 目录已在 `.gitignore` 中，但本地积累过多仍会占磁盘。

---

## 扩展点（备忘）

如未来需要更精细的控制（如仅 broken 时生成、按模块分别决策），可考虑：
- 使用 `session.testsfailed`（pytest 内置属性）替代手动标记
- 在 `generate_html_report` 内部根据 stats 决定是否写文件

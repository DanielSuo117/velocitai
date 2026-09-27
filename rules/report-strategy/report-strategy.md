---
paths:
  - "conftest.py"
  - "pytest.ini"
---

# 测试报告策略

适用于：`framework/conftest.py` 的报告类 hook、根目录 `pytest.ini` 的产物配置。报告栈只有 allure 一套，不维护第二种 HTML 报告。

---

## 🔴 P0 · 失败即截图，附进 allure

**触发**：用例在 setup 或 call 阶段失败时。

**规则**：`pytest_runtest_makereport` 对失败用例截图并 `allure.attach`，同时附上失败时的 URL。截图过程的任何异常都要吞掉，不能掩盖用例本身的失败；teardown 阶段不截图，page 可能已关闭。

❌ 反例：截图异常向外抛，"断言失败"被改写成"截图失败"

```python
if report.failed:
    allure.attach(page.screenshot(), ...)   # page 已关闭时这里抛错，真实失败原因被覆盖
```

✅ 正例：只截 setup / call，异常兜底

```python
if report.when in ("setup", "call") and report.failed:
    try:
        allure.attach(page.screenshot(), name=..., attachment_type=allure.attachment_type.PNG)
    except Exception:
        pass
```

---

## 🟡 P1 · 产物落点固定，HTML 报告按需生成

**触发**：配置 pytest 产物目录、需要查看报告时。

**规则**：allure 结果由 `pytest.ini` 的 `--alluredir=reports/allure-results` 固定写入，`reports/` 整体 gitignore。HTML 报告不在 session 结束时自动生成，需要时 `allure serve` 或 `allure generate … --clean`，避免全绿报告堆积。

❌ 反例：在 `pytest_sessionfinish` 里每次运行都生成一份 HTML 报告

✅ 正例：结果目录固定，报告由人按需生成（命令见 test-runner skill）

---

## 🟡 P2 · 运行日志走 pytest 内置 log_file

**触发**：需要事后查看某次运行的完整日志时。

**规则**：`pytest.ini` 配置 `log_file = reports/pytest.log` 与 `log_file_level = INFO`，框架 logger 保持向 root 传播，日志由 pytest 统一落盘，每次运行覆盖。不写自定义日志轮转。

❌ 反例：在 conftest 里手写 FileHandler、软链接和轮转清理

✅ 正例：两行 ini 配置，零自定义代码

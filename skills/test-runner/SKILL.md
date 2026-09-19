---
name: test-runner
description: 运行 pytest + 结构化分析失败原因。触发：运行测试、跑测试、run test、pytest、失败分析、allure。
---

# Test Runner — 运行测试与结果分析

> **⚠️ 运行前必须向用户确认 `--env`**（见 [agent-behavior.md](../../rules/agent-behavior/agent-behavior.md) P0.2）。
> 即使 `config/settings.py::DEFAULT_ENV="prod"`、即使下方示例写 `--env=<pre|prod>`（示例 ≠ 默认值），仍必须问用户。

## 运行前准备

```bash
# 确认虚拟环境已激活
source .venv/bin/activate

# 确认依赖已安装
pip list | grep -E "playwright|pytest|allure"
```

---

## 运行模式

所有测试均基于真实环境（URL + token）运行。

### 模式 1: 单个 story（调试 / 定位符验证）

**场景：** 替换定位符后验证、调试单个页面回归点

```bash
# 对应角色
pytest framework/tests/<role>/test_<role>_flow.py --env=<pre|prod> -v -k "test_xxx"
# 对应角色
pytest framework/tests/<role>/test_<role>_home.py --env=<pre|prod> -v -k "test_<case_name>"
```

### 模式 2: 按角色 / 全量回归

**场景：** 发版前验证、完整回归

```bash
# <角色A>全量
pytest framework/tests/<roleA>/ --env=<pre|prod>
# <角色B>全量
pytest framework/tests/<roleB>/ --env=<pre|prod>
# 全量
pytest framework/tests/ --env=<pre|prod>
```

### 查看 Allure 报告

```bash
# 启动报告服务器查看（运行完测试后直接可用）
allure serve reports/allure-results

# 生成静态报告（可部署）
allure generate reports/allure-results -o reports/allure-report --clean
```

---

## 结果分析

### pytest 输出解读

```
tests/test_xxx.py::TestXxx::test_method PASSED    → 通过
tests/test_xxx.py::TestXxx::test_method FAILED    → 失败（需分析）
tests/test_xxx.py::TestXxx::test_method ERROR     → fixture/setup 异常
tests/test_xxx.py::TestXxx::test_method SKIPPED   → 跳过
```

### 失败分类与处理

拿到失败输出后按症状查表，对号入座 →
[references/failure-triage.md](./references/failure-triage.md)

## 结果摘要模板

向用户汇报运行结果时套用 →
[references/report-template.md](./references/report-template.md)

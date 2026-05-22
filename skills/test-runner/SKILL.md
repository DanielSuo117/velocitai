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
pytest tests/<role>/test_<role>_flow.py --env=<pre|prod> -v -k "test_xxx"
# 对应角色
pytest tests/<role>/test_<role>_home.py --env=<pre|prod> -v -k "test_<case_name>"
```

### 模式 2: 按角色 / 全量回归

**场景：** 发版前验证、完整回归

```bash
# <角色A>全量
pytest tests/<roleA>/ --env=<pre|prod>
# <角色B>全量
pytest tests/<roleB>/ --env=<pre|prod>
# 全量
pytest tests/ --env=<pre|prod>
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

运行失败后，按以下分类诊断：

#### 类型 A: 定位符失效

**特征：**
```
TimeoutError: Timeout 10000ms exceeded.
  waiting for locator("text=<功能名>")
```

**处理：** 触发 `locator-replacer` skill，使用 agent-browser 访问真实页面重新抽取定位符（工具选型遵循 [agent-behavior P0.4](../../rules/agent-behavior/agent-behavior.md)）。

#### 类型 B: 页面加载超时

**特征：**
```
TimeoutError: page.wait_for_load_state: Timeout 30000ms exceeded.
  waiting for "networkidle"
```

**处理：**
1. 检查网络连通性（hosts 配置、VPN）
2. 检查 token 是否过期
3. 增大 `DEFAULT_TIMEOUT`（临时措施）

#### 类型 C: 断言失败

**特征：**
```
AssertionError: <页面中文名>加载失败
assert False
```

**处理：**
1. 页面是否正确导航到目标 URL
2. `PAGE_IDENTIFIER` 定位符是否仍然有效
3. 页面内容是否因版本更新发生变化

#### 类型 D: 认证失败

**特征：**
```
AssertionError: Token 登录失败
```

**处理：**
1. 检查 `config/settings.py` 中的 token 是否有效
2. 检查 `--env` 参数是否选对
3. 检查本地 hosts 是否指向正确的服务器 IP

#### 💡 快速排查建议

当失败需要深入排查时（定位符失效、页面结构变化等），建议进入 [quick-debug](../quick-debug/SKILL.md) 模式：通过 token 免登直接跳转到问题页面，避免从登录重走完整流程。

---

## 结果摘要模板

运行完成后，按以下格式输出摘要：

```
## 测试运行摘要

**运行模式：** 单个 story / 主流程全量
**环境：** pre / prod
**时间：** 2026-04-15 15:30

### 结果

| 状态 | 数量 |
|------|------|
| PASSED | X |
| FAILED | X |
| ERROR | X |
| SKIPPED | X |

### 失败详情（如有）

| 测试用例 | 失败类型 | 原因 | 建议操作 |
|----------|---------|------|---------|
| test_xxx | A: 定位符失效 | text=xxx 不唯一 | 使用 locator-replacer |
| test_yyy | D: 认证失败 | token 过期 | 更新 settings.py |
```


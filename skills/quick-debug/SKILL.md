---
name: quick-debug
description: 测试失败时免登跳转原地排查修复。触发：排查、纠错、debug、定位符失败、超时、元素找不到、断言失败。
---

# Quick Debug — 快速纠错验证

## 核心思路

**跳过从登录到问题节点的完整流程，直接免登到目标页面原地排查。**

利用项目已有的 token URL 免登机制，配合浏览器工具直接在问题页面进行 DOM 探索、定位符验证、等待策略调整，修复后原地验证，全程不重跑完整测试流程。

---

## 主干流程（5 步）

```
Step 1: 解析失败信息
    ↓
Step 2: 构造免登跳转 URL
    ↓
Step 3: 免登跳转到目标页面
    ↓
Step 4: 诊断问题（决策树）
    ↓
Step 5: 修复 + 原地验证
```

### Step 1: 解析失败信息

从堆栈 / 用户描述提取：失败用例名、错误类型（TimeoutError / AssertionError）、失败定位符、失败时所在 URL。信息不足时读取测试代码反推。

### Step 2: 构造免登跳转 URL

从配置文件读取对应环境的 token。

**⚠️ 免登前必须向用户确认 `--env`**（见 [agent-behavior P0.2](../../rules/agent-behavior/agent-behavior.md)）。

**两种情况：**

| 情况 | 策略 |
|------|------|
| 目标页面有明确 URL 路径 | 先免登（`/entry?token=<JWT>`），再导航到目标路径 |
| 目标页面需要交互才能到达（弹窗、新 tab 等） | 免登到最近的可直接访问的父级页面，执行最少量的导航操作到达目标 |

### Step 3: 免登跳转到目标页面

`browser_navigate → <base_url>/entry?token=<JWT>` → 导航到目标路径 → 验证 `is_page_loaded()`。免登失败（跳回登录页）→ 提示用户刷新 token。

### Step 4: 诊断问题

见下一节「诊断决策树」。

### Step 5: 修复 + 原地验证

**根据诊断结果调用对应 skill：**

| 诊断结果 | 调用 skill |
|---------|-----------|
| 定位符问题 | [locator-replacer](../locator-replacer/SKILL.md) |
| 等待策略问题 | [wait-strategy](../wait-strategy/SKILL.md) |
| 页面加载断言问题 | [page-load-assertion](../page-load-assertion/SKILL.md) |
| 页面大改版 | 报告用户，建议 [gen-page-test](../gen-page-test/SKILL.md) 重新生成 |
| 断言预期值变更 | 报告差异，由用户决策是否更新预期值 |

**原地验证：** 修复后在当前浏览器页面直接验证（用 Playwright MCP 重新执行失败操作），确认无误后建议用户重跑完整测试。

---

## 诊断决策树（Step 4 展开）

走到 Step 4 需要判断根因时展开 →
[references/diagnosis-tree.md](./references/diagnosis-tree.md)

## 浏览器工具选择

DOM 探索/定位符采集 → agent-browser（优先）；精确验证/断言 → Playwright MCP；agent-browser 未安装 → 全程 Playwright MCP（P0.4 降级）。

---

## 检查清单

每次 quick-debug 结束前，必须确认：

- [ ] 已明确失败原因并归类（A/B/C/D 哪个分支）
- [ ] 修复动作已执行（或已报告用户需人工决策）
- [ ] 原地验证通过（修复后的定位符/等待在当前页面生效）
- [ ] 建议用户重跑完整测试确认回归
- [ ] 保存操作验证失败时，参考 [save-verify-strategy](../save-verify-strategy/)（Toast 时序 / 重定向检测 / 数据对比）

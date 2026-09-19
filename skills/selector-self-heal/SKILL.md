---
name: selector-self-heal
description: 复核运行期自愈提案并写回 PageObject。触发：选择器失效、定位符漂移、自愈提案、proposals.jsonl、用例误报不通过。
---

# 选择器自愈 — 复核与写回

## 适用场景

- 带 `--self-heal=on|strict` 跑完回归后，终端汇总里出现「选择器自愈」段落
- 用例失败但功能实际正常，怀疑是定位符过期而非真实缺陷
- 需要把运行期的临时修复固化回源码

**不适用**：首次编写定位符（用 locator-replacer）；页面真的少了元素（那是真缺陷，不是漂移）。

---

## 机制分工

运行期只做两件事：找出可用的替代定位符让用例继续，并把提案写进
`reports/self-heal/proposals.jsonl`。**运行期绝不改源码。**
写回是本 skill 的职责，且要经人确认与落库闸门。

这条分界不是洁癖。测试进程里自动改源码，意味着一次跑飞的回归可以静默重写
整个 PageObject 层，而改动淹没在测试输出里没人看见。

---

## 复核流程

### 1. 读提案

```bash
python3 -c "import json;[print(json.dumps(json.loads(l),ensure_ascii=False,indent=2)) for l in open('reports/self-heal/proposals.jsonl')]"
```

每条提案含：`intent`（常量名、原选择器、注释说明、历史指纹）、
`candidates`（全部候选及置信度与理由）、`chosen`（运行期实际采用者，可能为 null）。

### 2. 逐条判定

| 现象 | 结论 |
|------|------|
| `chosen` 为 null，且候选列表为空 | 元素真的不在了 → **真缺陷**，不要写回，去查功能 |
| `chosen` 的 strategy 是 `testid` 或 `id` | 锚点稳定 → 可写回 |
| `chosen` 的 strategy 是 `text` | 文案改动即失效 → 写回前先找有没有 testid 可用 |
| `chosen` 的 strategy 是 `stable-class` | 样式重构即失效 → 优先向前端要 testid |
| 同一常量反复出现在提案里 | 该定位符本身选得不好 → 重新设计，别反复打补丁 |

**触发**：`chosen` 非 null 但 `intent` 的指纹字段全为 null 时，必须人工确认——
没有历史指纹意味着判定只依赖注释说明，证据比平时弱。

### 3. 写回

写回目标是 PageObject 类顶部的定位符常量，**只改选择器字符串，不动常量名**：

```python
# 改前
LOGIN_BUTTON = "#login-btn"          # P0: 登录按钮
# 改后
LOGIN_BUTTON = '[data-testid="login-submit"]'   # P0: 登录按钮
```

常量名是全项目引用点，改名会波及所有用例；注释是下次自愈的意图来源，
删掉等于自断依据。

### 4. 收尾

- 写回后重跑该用例，不带 `--self-heal`，确认真绿
- 确认后清空 `proposals.jsonl`，避免旧提案被反复复核
- 若修改涉及定位策略的通用经验，按自我进化机制沉淀（先过落库闸门）

---

## 禁止事项

- 不要把 `chosen` 为 null 的提案「想办法修好」——那是真缺陷的信号
- 不要为了让用例变绿而放宽 `MIN_CONFIDENCE`
- 不要批量写回：逐条看 strategy 与 confidence，低置信的宁可留着人工处理

相关：[自愈边界规则](../../rules/playwright/self-healing-boundaries.md) ·
[locator-replacer](../locator-replacer/) · [落库闸门](../../rules/agent-behavior/evolution-gate.md)

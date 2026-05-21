---
paths: []
---

# Playwright 使用规范

> 本文件是导航索引（`paths: []` 不自动加载），子规则文件各自声明 paths 按需加载。需要时通过 CLAUDE.md 路由表或 rules-index.md 跳转到此。

---

## 子规则索引

| 主题 | 文件 | 关键词 |
|------|------|--------|
| 超时排查 & 等待策略 | [timeout-and-wait.md](./timeout-and-wait.md) | TimeoutError、page.url、新 tab、networkidle、SPA 渲染 |
| 定位符策略 | [locator-strategy.md](./locator-strategy.md) | 禁止项、ARIA role、链式 `>>`、精确匹配 |
| 新 tab 检测 | [new-tab-detection.md](./new-tab-detection.md) | expect_page、window.open、target="_blank" |
| 浏览器上下文 | [browser-context.md](./browser-context.md) | context 共享、跨域隔离、class 级 |
| 断言模式 | [assertion-patterns.md](./assertion-patterns.md) | Toast、UI 状态变更、等待目标唯一性 |
| 第三方组件 | [third-party-components.md](./third-party-components.md) | Arco Design、下拉框关闭 |
| Performance API 隔离 | [performance-api-isolation.md](./performance-api-isolation.md) | clearResourceTimings、跨用例污染、批量失败 |

## 交叉引用

- 定位符完整六级优先级 → [locator-replacer skill](../../skills/locator-replacer/SKILL.md)
- 等待策略详细方法论 → [wait-strategy skill](../../skills/wait-strategy/SKILL.md)
- Agent 浏览器工具选型 → [agent-behavior](../agent-behavior/agent-behavior.md) P0.4

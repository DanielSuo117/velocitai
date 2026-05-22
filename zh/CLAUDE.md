# UI 回归测试 — 项目地图

> Python + Playwright + pytest POM 回归框架。本文件是 agent 唯一入口索引。

---

## 行为边界（开工前必读）

运行测试前必须确认 `--env`；Git 操作需用户授权；文档与代码冲突时必须询问。

完整条款 → [agent-behavior.md](./rules/agent-behavior/agent-behavior.md)

---

## 路由表

| 要做什么 | 去哪里 |
|---------|--------|
| **新建**页面对象 + 测试 | [gen-page-test](./skills/gen-page-test/) |
| **增加**已有页面的回归点 | [add-regression-point](./skills/add-regression-point/) |
| **替换**定位符 / 分析 DOM | [locator-replacer](./skills/locator-replacer/) |
| **运行**测试 / 分析结果 | [test-runner](./skills/test-runner/) |
| **排查**测试失败 | [quick-debug](./skills/quick-debug/) |
| 设计 **is_page_loaded** | [page-load-assertion](./skills/page-load-assertion/) |
| 配置**等待策略** | [wait-strategy](./skills/wait-strategy/) |
| 配置**浏览器** viewport/超时 | [browser-config](./skills/browser-config/) |
| 用例**往返闭合** | [case-round-trip](./skills/case-round-trip/) |
| **保存验证**策略 | [save-verify-strategy](./skills/save-verify-strategy/) |
| **架构**决策 / 分层 / 新角色 | [architecture](./skills/architecture/) |
| **代码审查** / 探索 / 重构 | [code-review-graph](./skills/code-review-graph/) |
| 组合场景（多 skill 串联） | [SKILL.md](./skills/SKILL.md) |
| **编码规范**（命名/基类/用例） | [coding-conventions](./rules/coding-conventions/coding-conventions.md) |
| **Playwright 规则**索引 | [playwright-overview](./rules/playwright/playwright-overview.md) |
| **Performance API 隔离** | [performance-api-isolation](./rules/playwright/performance-api-isolation.md) |
| **测试报告生成策略** | [report-strategy](./rules/report-strategy/report-strategy.md) |
| PageObject 清单 | [docs/pages-catalog.md](./docs/pages-catalog.md) |
| 回归测试点 | [docs/regression-points.md](./docs/regression-points.md) |
| 项目架构落地 | [docs/architecture.md](./docs/architecture.md) |
| 环境搭建 | [docs/setup.md](./docs/setup.md) |

---

## 自我进化机制（P0 最高优先级）

**触发**：任务完成前 / 踩坑 / 用户纠正 / 同类问题复现。

| 类型 | 沉淀目标 |
|------|---------|
| 经验（How-to） | `skills/` 对应 SKILL.md |
| 规则（Must/Must-not） | `rules/<主题>/` 对应子文件（必含 ❌反例 + ✅正例） |
| 项目事实（类名/URL/清单） | `docs/` 对应文件 |

执行：Edit 最小增量写入；回复末尾声明 `📝 已沉淀至 <file>：<摘要>`。

---

## 命令

```bash
source .venv/bin/activate

# 按模块运行（--env 必须由用户指定）
pytest tests/<role>/test_<role>_flow.py --env=<pre|prod>

# 全量回归
pytest tests/ --env=<pre|prod>

# 报告
allure serve reports/allure-results
```

私有备忘：[CLAUDE.local.md](./CLAUDE.local.md)（不入库）。

---

## 工具与代理

- **code-review-graph MCP**：探索代码库时优先使用图谱工具，再降级到 Grep/Glob/Read。工作流方法论 → [code-review-graph skill](./skills/code-review-graph/)
- **code-reviewer 代理**：代码审查与缺陷验证 → [code-reviewer.md](./.claude/agents/code-reviewer.md)

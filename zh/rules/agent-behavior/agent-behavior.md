# Agent 行为规则

适用于：agent 自身的决策流程（跨所有 skill / rule / 代码）

---

## 🚦 边界速查表

### 行为边界

| 类别 | 可做 | 必须先询问 | 禁止 |
|------|------|-----------|------|
| 代码改动 | 编辑 `pages/` / `tests/` / `config/` / `conftest.py` | —— | —— |
| 测试运行 | —— | 环境（`--env=pre` / `--env=prod`）、范围 | 自行默认 `--env=prod` |
| 文档代码冲突 | —— | 向用户说明冲突点 + 两个方案，由用户决定 | 自行选边、无声纠偏 |
| Git | 只读 + `git add`（仅暂存） | 明确授权才可 `commit` / `push` | 自动 `commit` / `push` / `--amend` / `--force` |

项目事实速查（架构 / PageObject / 回归点 / 环境搭建）→ [CLAUDE.md 路由表](../../CLAUDE.md)

---

## 🔴 P0.1 · 文档与代码不一致时必须询问

**触发**：发现 `docs/` / `skills/` / `rules/` 内容与源码冲突。

**规则**：禁止自行选边或无声纠偏，必须向用户说明冲突点 + 两个方案，由用户决定后再动手。

❌ 反例：发现 skill 示例是 `--env=pre` 而 `DEFAULT_ENV="prod"`，直接按 skill 照抄或默默改掉其中一方。

✅ 正例：向用户汇报「skill 示例用 `pre`，代码默认 `prod`，请确认以哪边为准」。

---

## 🔴 P0.2 · 运行测试前必须确认 `--env`

**触发**：用户请求跑测试但未明确 `--env=pre` 或 `--env=prod`。

**规则**：禁止自行默认任何环境，必须先询问环境和范围，再执行。

❌ 反例：

```
用户：运行测试用例
agent：pytest tests/<role>/test_<role>_flow.py --env=prod -v   # 自行默认 prod
```

✅ 正例：

```
用户：运行测试用例
agent：请确认环境：--env=pre 还是 --env=prod？范围是全量还是 -k <case>？
```

---

## 🔴 P0.3 · Git 提交与推送仅由用户执行

**触发**：完成代码/文档改动准备入库时。

**规则**：禁止 `git commit` / `git push`（含 `--amend` / `--force`）。改动完成后列摘要 + 提议 commit message，提示用户手动执行。用户明确授权时例外，授权仅对当次生效。

❌ 反例：写完代码后 `git add && git commit -m "feat: ..."` 自动提交。

✅ 正例：

```
✅ 已完成：
- 新增 pages/xxx.py（新 PageObject）
- 修改 tests/xxx.py（补测试用例）
建议 commit message：feat(pages): 新增 XX 页面对象 + 对应用例
请手动执行：git add pages/xxx.py tests/xxx.py && git commit
```

---

## 🔴 P0.4 · 浏览器工具选型：agent-browser 抓取 / Playwright MCP 验证

**触发**：需要通过浏览器交互时。

**规则**：DOM 探索 / 定位符采集用 `agent-browser`（~200–400 tokens/次）；回归验证 / 断言校验用 Playwright MCP；`agent-browser` 未安装时全部降级到 Playwright MCP。

P0.4.1–P0.4.4 详细反例/正例见 [browser-tool-usage.md](./browser-tool-usage.md)。

---

P0.5–P0.7（Skill 编写规则）→ 仅在编辑 `skills/**` 时加载 → [skill-authoring.md](./skill-authoring.md)

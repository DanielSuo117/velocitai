---
name: locator-replacer
description: 替换占位定位符为真实选择器（六级优先级）。触发：替换定位符、locator、selector、定位失败、元素找不到、DOM 分析。
---

# Locator Replacer — 定位符替换 Skill

## 适用场景

- 将页面对象中 `text=` 占位定位符替换为真实选择器
- 前端构建后原有选择器失效，需要重新定位
- 新增页面元素需要选择最佳定位策略

---

## 定位符选择策略（六级优先级）

按优先级从高到低，**逐级尝试，选中即停**。优先使用页面上已有的语义化信息，
避免依赖需要前端额外配合的属性。

| 级别 | 策略 | 抗什么 | 代价 |
|------|------|--------|------|
| **P0** | ARIA role + 可见文本 | CSS 重构、构建哈希 | 文案变更需同步 |
| **P1** | 可见文本 | CSS 重构、构建哈希 | 文案变更需同步、可能不唯一 |
| **P2** | 表单特有属性（name/placeholder/type） | 样式与文案变更 | 仅适用于表单控件 |
| **P3** | 语义化 CSS class / id | 文案变更 | 样式重构即失效 |
| **P4** | `data-testid` | 几乎全部 | **需前端配合添加** |
| **P5** | 相对 XPath / CSS 结构 | —— | 最脆弱，最后手段 |

**完整写法、判断依据与代码示例** → [references/priority-levels.md](./references/priority-levels.md)

## 执行流程

### Step 1: 分析目标页面 DOM

使用 agent-browser 打开目标页面，获取交互元素信息（工具选型遵循 [agent-behavior P0.4](../../rules/agent-behavior/agent-behavior.md)，agent-browser 未安装时降级到 Playwright MCP）：

```
操作步骤：
1. browser_navigate → 访问目标页面（已认证状态）
2. browser_snapshot → 获取页面无障碍树（accessibility tree）
3. browser_evaluate → 执行 JS 提取元素属性：
   - document.querySelectorAll('[data-testid]')  → 已有 testid
   - document.querySelectorAll('[role]')          → ARIA role
   - document.querySelectorAll('button, a, input') → 交互元素
```

### Step 2: 为每个元素选择定位策略

对照页面对象中的每个占位定位符，按 P0→P5 逐级尝试，命中即停：

| 检查顺序 | 条件 | 使用 |
|---------|------|------|
| P0 | 有 role + name | `role=button[name='...']` |
| P1 | text= 唯一且稳定 | `text=...`（标记"已验证唯一"）|
| P2 | 表单属性（placeholder/name/type） | `[placeholder='...']` |
| P3 | 稳定 CSS class（非哈希） | `css=.xxx` |
| P4 | 有 data-testid | `[data-testid='...']` |
| P5 | 以上均无 | 相对 XPath（≤3 层） |

### Step 3: 更新页面对象

```python
class <PageName>(BasePage):
    # 定位符 — 已替换为真实选择器（<日期>）
    <PRIMARY_ACTION_BTN> = "role=button[name='<按钮文案>']"  # P0: ARIA role
    <SECONDARY_LINK> = "text=<链接文案>"                      # P1: text（已验证唯一）
    PAGE_IDENTIFIER = "role=heading[name='<页面标题>']"       # P0: ARIA role
```

**更新规则：**
- 在定位符行尾注释标注选择级别（`# P0: ARIA role` / `# P1: text` / ... / `# P4: testid` / `# P5: XPath`）
- 如果 `text=` 经验证确实稳定且唯一，注释标记 `# P1: text（已验证唯一）`
- 删除原来的 `# 定位符 — 后续替换为实际选择器` 注释
- 更新为 `# 定位符 — 已替换为真实选择器（日期）`

### Step 4: 验证

```bash
# 在对应角色的回归文件中跑指定用例（运行前向用户确认 --env，见 agent-behavior P0.2）
pytest framework/tests/<role>/test_<role>_flow.py --env=<pre|prod> -v -k "test_<story_name>"
```

### Step 5: 同步更新文档

更新 [docs/regression-points.md](../../docs/regression-points.md) 中对应 PageObject 的"关键定位符"段。

---

## 定位符质量检查清单

替换完成后，逐项确认：

- [ ] 没有使用绝对 XPath（`/html/body/...`）
- [ ] 没有使用哈希类名（`sc-xxx`, `css-xxx`, `_module_xxx`）
- [ ] 没有使用纯数字索引（`div[3]`，除非列表取第 N 项）
- [ ] 每个定位符行尾标注了选择级别（`# P0` ~ `# P5`）
- [ ] XPath 层级不超过 3 层
- [ ] 主流程测试在真实环境通过

---

## 常见问题处理

同一文本重复、元素无稳定属性、构建后批量失效等症状的处理方式 →
[references/troubleshooting.md](./references/troubleshooting.md)

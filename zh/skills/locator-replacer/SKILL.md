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

按优先级从高到低，**逐级尝试，选中即停**。优先使用页面上已有的语义化信息，避免依赖需要前端额外配合的属性：

### P0: 用户可见的语义化元素（Role + Text）

```python
# 通过 ARIA role + 可见文本定位
LOGIN_BTN = "role=button[name='登录']"
NAV_LINK = "role=link[name='<功能名>']"
SEARCH_INPUT = "role=textbox[name='搜索']"
```

- 基于无障碍语义，与用户看到的界面一致
- 抗 CSS 重构：role 不依赖 class/id
- 抗构建工具：不受 Webpack/Vite 哈希类名影响
- **中文文案变更时需要同步更新**

### P1: 可见文本定位

```python
# 精确匹配
FEATURE_BTN = "text=<功能名>"
# 包含匹配（文本可能嵌套在子元素中）
FEATURE_TAB = "text=<功能名>"
```

- 简单直接，不依赖任何额外属性
- 适合文案稳定、元素唯一的场景
- **注意：** `text=` 是当前项目的占位方案，如果分析后发现 `text=` 已经足够稳定且元素唯一，可以保留并标记 `# P1: text（已验证唯一）`

### P2: 表单特有属性

```python
# placeholder 定位
EMAIL_INPUT = "[placeholder='请输入邮箱']"
# label 关联定位
PASSWORD_INPUT = "css=input[name='password']"
# type 属性
SUBMIT_BTN = "css=button[type='submit']"
```

- 仅适用于表单元素（input/select/textarea/button）
- `name` 属性通常由后端约定，相对稳定
- `placeholder` 跟随文案，稳定性中等

### P3: 稳定的 CSS Class / ID

```python
# 业务语义类名 — 稳定
COURSE_CARD = "css=.list-card"
LOGIN_FORM = "css=#login-form"
NAV_MENU = "css=.main-navigation"

# ⚠️ 以下是哈希类名 — 绝对禁止使用
# BAD: "css=.sc-bdVaJa.bVjGWg"         (styled-components 哈希)
# BAD: "css=.css-1a2b3c"                (CSS Modules 哈希)
# BAD: "css=[class*='_component_']"     (Vite CSS Modules)
```

**哈希类名识别规则（必须跳过）：**

| 构建工具 | 哈希类名特征 | 示例 |
|----------|-------------|------|
| styled-components | 随机字母组合 | `.sc-bdVaJa`, `.bVjGWg` |
| CSS Modules | 下划线 + 哈希 | `.header_abc123`, `._component_1x2y3` |
| Vite | 短哈希后缀 | `.module_1a2b3c` |
| Tailwind JIT | 动态工具类 | `.[\31 /2]`, `.[color:red]` |
| Emotion | 前缀 css- | `.css-1a2b3c` |

**可用的类名特征：**
- 包含业务语义：`.list-card`, `.login-form`, `.nav-menu`
- 遵循 BEM 命名：`.header__title`, `.card--active`
- 带有明确前缀：`.app-feature-list`, `.app-header`

### P4: `data-testid` 专用测试属性

```python
# Playwright locator 写法
SUBMIT_BTN = "[data-testid='submit-button']"
```

- 不受样式重构、文案修改、构建工具影响
- **需要前端开发配合添加**，无法独立完成
- 适合 P0~P3 均无法稳定定位的复杂元素
- 如果页面已有 `data-testid`，可以直接使用，但不必强求前端为所有元素添加

### P5: 相对 XPath / CSS 结构定位（最后手段）

```python
# ✅ 相对路径 — 从稳定祖先节点出发
SUBMIT_BTN = "xpath=//div[@class='login-form']//button[@type='submit']"
FIRST_COURSE = "css=.course-list > .course-item:first-child"

# ❌ 绝对路径 — 绝对禁止
# BAD: "xpath=/html/body/div[1]/div[2]/ul/li[3]/button"
```

**XPath 编写规则：**
- 从离目标元素最近的稳定祖先节点开始
- 祖先节点用业务语义属性锚定（class/id/data-*）
- 路径层级不超过 3 层
- 禁止使用绝对路径（从 `/html/body` 开始）
- 禁止纯数字索引定位（`div[3]`），除非是列表且确实需要第 N 项

---

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
pytest tests/<role>/test_<role>_flow.py --env=<pre|prod> -v -k "test_<story_name>"
```

### Step 5: 同步更新文档

更新 [docs/regression-points.md](../../../docs/regression-points.md) 中对应 PageObject 的"关键定位符"段。

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

### 同一文本出现多次导致 `text=` 不唯一

降级到 P3/P5，用父容器 + 文本组合：`css=.list-card:first-child >> text=查看详情`

### 元素无任何稳定属性

向前端团队提出添加 `data-testid`（P4）需求，附元素清单；临时用 P5 相对 XPath 过渡。

### 前端构建后选择器批量失效

检查是否使用了哈希类名（违反 P3）→ 优先升级到 P0/P1（不受构建影响）→ 文案变更则对照新文案更新。

# 六级定位优先级 —— 完整说明与代码示例

> 由 [locator-replacer](../SKILL.md) 按需加载。
> SKILL.md 里的速查表足以做出选择；只有在需要具体写法或判断依据时才读本文。

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

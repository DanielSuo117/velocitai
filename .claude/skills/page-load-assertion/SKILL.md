---
name: page-load-assertion
description: is_page_loaded() 四种验证模式与调用层级。触发：页面断言、is_page_loaded、page loaded、页面加载验证。
---

# Page Load Assertion — 页面加载断言方法论

## 核心思路

页面"正常"的判断不是检查 HTTP 状态码，而是验证**用户能看到的关键元素确实渲染出来了**。通过每个 PageObject 的 `is_page_loaded()` 方法统一实现。

---

## `is_page_loaded()` 的四种验证模式

按严格程度从低到高：

### 模式 A：单元素验证（最简单）

检查该页面**独有的标志性容器**是否可见。适用于结构简单、一个元素就能区分的页面：

```python
PAGE_CONTAINER = "css=.feature-container"    # P3

def is_page_loaded(self) -> bool:
    return self.is_visible(self.PAGE_CONTAINER)
```

### 模式 B：双元素 AND 组合（推荐默认）

**容器 + 内容** 双重验证，确保"页面骨架到位 + 数据渲染完成"：

```python
PAGE_CONTAINER = "css=.feature-container"    # P3
PAGE_TITLE = "text=欢迎使用"                  # P1

def is_page_loaded(self) -> bool:
    return self.is_visible(self.PAGE_CONTAINER) and self.is_visible(self.PAGE_TITLE)
```

### 模式 C：多元素 + 激活态验证（最严格）

在结构和内容基础上，还验证**当前 UI 状态**（如某个 tab 处于 active）。适用于承担"起点状态判断"语义的页面：

```python
PAGE_TITLE = "css=span.page-title"                                    # P3
TAB_BAR = "css=ul.tab-bar"                                            # P3
DEFAULT_TAB_ACTIVE = "css=ul.tab-bar li.tab.active >> text=默认Tab"    # P3+P1

def is_page_loaded(self) -> bool:
    return (
        self.is_visible(self.PAGE_TITLE)
        and self.is_visible(self.TAB_BAR)
        and self.is_visible(self.DEFAULT_TAB_ACTIVE)
    )
```

注意：状态类 selector（`.active` / `aria-selected` 等）**必须配 text 锁定**，否则切换 tab 后 `.active` 跟随新激活对象漂移。

### 模式 D：委托给语义方法

把验证逻辑提取为有业务含义的方法名，便于 setup fixture 中单独调用：

```python
def is_page_loaded(self) -> bool:
    return self.is_login_success()

def is_login_success(self) -> bool:
    return self.is_visible(self.SUCCESS_FLAG) and self.is_visible(self.NAV_LIST)
```

---

## 模式选择决策树

```
新页面需要 is_page_loaded()
│
├─ 页面结构简单，一个独有容器即可区分？
│  └─ 是 → 模式 A（单元素）
│
├─ 需要确认内容也渲染到位？
│  └─ 是 → 模式 B（容器 + 内容，推荐默认）
│
├─ 该页面是复位 fixture 的起点，需要判断 UI 状态？
│  └─ 是 → 模式 C（多元素 + 激活态）
│
├─ 验证逻辑在 setup 中也需要单独调用？
│  └─ 是 → 模式 D（委托给语义方法）
│
└─ 容器可能存在但内容未渲染（SPA 子 Tab 切换 / 异步加载）？
   └─ 是 → 模式 E（JS evaluate 检查子元素数量）
```

---

## 验证元素的选择原则

| 原则 | 说明 |
|------|------|
| 选该页面独有的元素 | 不选通用 header/footer，选只有这个页面才有的容器或文本 |
| 优先选结构性容器 | 如 `.feature-container`、`.detail-wrapper`，页面骨架不易变 |
| 文本元素锁定业务语义 | 如 `text=欢迎使用`，确认内容渲染到位 |
| 状态类 selector 配 text | `.active` 会随操作漂移，必须加 `>> text=具体文本` 锁定 |
| 不选动态数据 | 具体数字、用户名等因数据变化导致断言不稳定 |

### 断言目标的三级稳定性

核心原则：优先选**模板级**文本（页面框架固定标题），禁止选**数据级**内容（动态计数、日期）。多视图场景中每个断言目标须同时满足「模板级 + 视图独占」。

完整规则与反例/正例 → [assertion-patterns.md](../../rules/playwright/assertion-patterns.md) "断言目标稳定性"章节。

### 模式 E：白屏检测 + 空数据 vs 有数据 三态判断

SPA 应用中，容器 div 可能存在于 DOM 且 `is_visible` 返回 true，但内部组件未挂载（白屏）。此时模式 A/B 的 `is_visible(容器)` 会误判为正常。

**页面内容区有三种状态，必须分别处理**：

```
页面内容区状态
│
├─ 白屏（渲染失败）
│  内容区子元素数 = 0，组件未挂载
│  → 判定：❌ 测试失败，报"内容区域未渲染，疑似白屏"
│
├─ 空数据（无业务数据但渲染正常）
│  内容区子元素数 > 0，但无业务数据项
│  通常有空状态提示（图片 + "暂无数据"/"还没有收藏题哦"等文案）
│  → 判定：✅ 渲染正常，页面确实没有业务数据
│
└─ 有数据（正常渲染）
   内容区子元素数 > 0，且有业务数据项
   → 判定：✅ 渲染正常
```

**实现模板**：

```python
# 定位符
CONTENT_CONTAINER = "css=<内容主容器>"                 # 页面骨架容器
EMPTY_STATE = "css=<空状态提示元素>"                    # 空状态组件（图片+文案）
DATA_ITEM = "css=<业务数据项>"                          # 单个数据条目

def get_content_render_state(self) -> str:
    """返回内容区渲染状态：'blank' / 'empty' / 'loaded'。"""
    return self.page.evaluate("""() => {
        const container = document.querySelector('<内容主容器选择器>');
        if (!container) return 'blank';
        const contentArea = container.querySelector('<内容区域选择器>');
        if (!contentArea || contentArea.children.length === 0) return 'blank';
        return 'loaded';
    }""")

def is_content_rendered(self) -> bool:
    """白屏检测：容器存在但内容区无子元素 → False。
    空数据和有数据都算渲染成功 → True。"""
    return self.get_content_render_state() != 'blank'

def has_data_items(self) -> bool:
    """是否有业务数据（排除空状态）。"""
    return self.get_element_count(self.DATA_ITEM) > 0
```

**用例中的三态断言**：

```python
# 第一层：渲染检测（白屏 vs 已渲染）
is_rendered = page_obj.is_content_rendered()
if not is_rendered:
    assert False, "内容区域未渲染，疑似白屏"

# 第二层（可选）：空数据 vs 有数据
# 根据业务预期决定是否需要进一步区分
if page_obj.has_data_items():
    # 有数据 → 可以进一步验证数据内容
    pass
else:
    # 空数据 → 记录到报告，不视为失败
    allure.attach("该Tab当前无业务数据（空状态）", ...)
```

**⚠️ 陷阱**：

| 错误做法 | 问题 | 正确做法 |
|---------|------|---------|
| `innerText.length > N` 判断白屏 | 空状态提示文案可能很短，被误判为白屏 | `children.length > 0` |
| 空数据等同于失败 | 无收藏/无错题是合理的业务状态 | 白屏才失败，空数据只记录 |
| 只检查容器 `is_visible` | 容器 div 可能存在但子组件未挂载 | JS evaluate 检查子元素 |

**适用场景**：
- 同一容器内切换多个子 Tab，部分 Tab 可能无业务数据
- 异步加载组件可能因接口超时未渲染
- 页面骨架先渲染、内容延迟加载的 SPA 路由

---

## 调用层级

1. **class setup**：登录后 `assert home.is_page_loaded(), "首页加载失败"`
2. **function reset**：`if not self.home.is_page_loaded(): click_nav_home(); assert ...`
3. **用例体**：每次跳转后 `assert target.is_page_loaded(), "<页面>加载失败"`

---

## 规则约束

1. **每个 PageObject 必须实现 `is_page_loaded()`**——返回 `bool`，放在类的最后一个方法
2. `is_page_loaded()` 内部只用 `is_visible()` 组合，**不抛异常**

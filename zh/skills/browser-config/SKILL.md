---
name: browser-config
description: 浏览器 viewport / headless / 超时分层配置。触发：viewport、浏览器配置、导航超时、headless、slow_mo、incognito。
---

# 浏览器启动配置 — viewport / 无痕 / 超时分离

## 核心原则

**所有浏览器配置集中声明在配置文件，通过 fixture 分层注入，禁止在用例或 PageObject 中硬编码。**

---

## 一、pytest 浏览器完整配置架构

### 配置分层

```
配置文件（常量声明）
  │
  ├─ browser fixture（session 级）
  │    └─ headless / slow_mo / incognito
  │
  ├─ page fixture（function 级）
  │    └─ viewport / timeout / navigation_timeout
  │
  └─ class_page fixture（class 级）
       └─ viewport / timeout / navigation_timeout
```

### 配置文件：所有常量集中声明

```python
# 浏览器配置
HEADLESS = False              # True: 无头模式（CI 环境）; False: 有头模式（本地调试）
SLOW_MO = 500                 # 每步操作间隔（ms），便于肉眼观察；CI 设为 0
DEFAULT_TIMEOUT = 15000       # 元素操作超时（ms）
DEFAULT_NAVIGATION_TIMEOUT = 15000  # 页面导航超时（ms）
VIEWPORT_WIDTH = 1280         # 视口宽度
VIEWPORT_HEIGHT = 900         # 视口高度
```

### Fixture 分层模板

```python
@pytest.fixture(scope="session")
def browser(playwright_instance):
    browser = playwright_instance.chromium.launch(
        headless=HEADLESS, slow_mo=SLOW_MO, args=["--incognito"],
    )
    yield browser
    browser.close()

@pytest.fixture                   # function 级：每个用例独立 context + page
def page(browser):
    context = browser.new_context(viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
    page = context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT)
    page.set_default_navigation_timeout(DEFAULT_NAVIGATION_TIMEOUT)
    yield page
    page.close(); context.close()

@pytest.fixture(scope="class")    # class 级：同 class 内共享 context + page
def class_page(browser):
    # 同 page fixture，scope="class"
    ...
```

**关键约束**：`viewport` 在 context 层、`timeout` 在 page 层、`--incognito` 在 browser 层——三者不得混用层级。

---

## 二、Viewport 尺寸选择

### 核心约束：viewport 高度必须适配物理屏幕

viewport 高度不能超过物理屏幕可用高度（屏幕分辨率 − 浏览器工具栏 − 系统任务栏），否则浏览器窗口底部超出屏幕，页面底部内容被遮挡、无法交互。

### 正确策略：保持宽度，适当增加高度（不超出屏幕）

响应式页面等比放大 viewport 无效（可见比不变）；应保持宽度，适当增加高度（不超出屏幕）。

| 方案 | Viewport | 效果 |
|------|----------|------|
| 默认 | 1280x720 | 基准，较小 |
| **推荐** | **1280x900** | **适配 MacBook 屏幕，窗口不超出屏幕** |
| 外接显示器 | 1280x1080 | 适配 Full HD 显示器 |
| 过大（错误） | 1280x1440 | 超出多数屏幕，底部被遮挡 |
| 等比放大（错误） | 2560x1440 | 响应式页面可见比无改善 |

---

## 三、无痕模式（Incognito）

pytest 测试浏览器启用（隔离环境），MCP 调试浏览器视需求（可能需要保留登录态）。通过 `launch(args=["--incognito"])` 在 browser 层传入。

---

## 四、导航超时与元素超时分离

两者默认均为 15s。分离的意义：页面资源重时可**单独调大导航超时**而不影响元素操作的快速反馈。

```python
page.set_default_timeout(DEFAULT_TIMEOUT)                    # 元素操作
page.set_default_navigation_timeout(DEFAULT_NAVIGATION_TIMEOUT)  # 页面跳转
```

---

## 检查清单

- [ ] `viewport` 在 `new_context()` 时传入（context 层），不在 browser 层
- [ ] `set_default_timeout` 与 `set_default_navigation_timeout` 均已设置（两者分离）
- [ ] `--incognito` 在 pytest 测试浏览器上启用，MCP 调试浏览器视需求
- [ ] 用例和 PageObject 中无硬编码的浏览器配置值

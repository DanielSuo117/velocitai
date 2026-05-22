---
paths:
  - "pages/**"
  - "tests/**"
  - "conftest.py"
---

# 代码与测试规范

适用于: `pages/**` 与 `tests/**`。只写基于真实浏览器的端到端回归测试，不写 mock 单元测试。

---

## Python 命名

- 类名 PascalCase / 方法·变量 snake_case / 常量·定位符 UPPER_SNAKE_CASE

方法命名前缀约定：

| 交互类型 | 前缀 | 示例 |
|----------|------|------|
| 点击按钮/链接/Tab | `click_` | `click_submit()` |
| 填写输入框 | `fill_` | `fill_search(keyword)` |
| 选择下拉/筛选 | `select_` | `select_type()` |
| 获取文本 | `get_xxx_text` | `get_title_text()` |
| 等待元素 | `wait_for_` | `wait_for_loading_done()` |
| 页面加载验证 | `is_page_loaded` | `is_page_loaded()` → 每个页面**必须**有 |

**导入顺序**：标准库 → 第三方库（`allure`, `playwright`） → 项目内模块（`from pages.xxx import ...`）

---

## PageObject 约定

- 所有页面类继承 `BasePage`；文件首行加 `# 页面名称：<中文名>`
- 定位符声明为**类级别常量**（类顶部），行尾标注优先级 `# P0`~`# P5`（策略见 [locator-replacer/SKILL.md](../../skills/locator-replacer/SKILL.md)）
- 定位符**必须**声明为类级别常量，**禁止**在方法内硬编码选择器字符串
- `BasePage` 已封装的通用操作（`click` / `fill` / `is_visible` / `get_text` / `wait_for_element` / `get_element_count`）**优先使用**，避免重复实现
- `BasePage` 未覆盖的 Playwright API（`self.page.context.expect_page()`、`self.page.keyboard`、`self.page.wait_for_timeout()`、`self.page.locator().wait_for(state="hidden")`、`self.page.eval_on_selector()` 等）可直接通过 `self.page` 调用
- 不在 PageObject 里写断言（`is_page_loaded` 除外）；`is_page_loaded` 必须实现，放类末尾

❌ 反例：方法内硬编码选择器

```python
def click_some_button(self):
    self.click("css=.some-button")              # 选择器散落在方法里，无法统一维护
```

✅ 正例：定位符集中管理 + 优先用 BasePage 封装

```python
# 页面名称：<页面中文名>
from pages.base_page import BasePage
class SomeFeaturePage(BasePage):
    FEATURE_TITLE = "css=span.feature-title"  # P3
    LEFT_MENU = "css=ul.menu-box"             # P3
    LOADING = "css=.loading-state"            # P3

    def get_title(self) -> str:
        return self.get_text(self.FEATURE_TITLE)           # BasePage 已封装，优先使用

    def wait_for_loading_done(self, timeout=30000):
        self.page.locator(self.LOADING).wait_for(         # BasePage 未封装 state="hidden"，
            state="hidden", timeout=timeout,              # 可直接用 self.page
        )

    def is_page_loaded(self) -> bool:
        return self.is_visible(self.FEATURE_TITLE) and self.is_visible(self.LEFT_MENU)
```

---

## 测试文件组织

- 文件首行加 `# 文件用途：<中文概述>`；每文件对应一个 `Test<Role><Feature>` 类
- 按角色拆分目录：`tests/<roleA>/`、`tests/<roleB>/`
- 基类路径：各角色 `tests/<role>/<role>_base_test.py::<Role>BaseTest`；公共根基类 `tests/base_test.py::BaseTest`

### 测试方法新增与修改顺序

- **新增**：追加到类末尾，禁止插入到已有方法之间
- **修改**：原位就地修改，禁止调换方法顺序

```python
class Test<Role>Flow(BaseTest):
    def test_case_a(self): ...   # 已有 — 原位改
    def test_case_b(self): ...   # 已有 — 保持顺序
    def test_case_c(self): ...   # 新增 — 追加末尾
```

---

## 基类约定（强制）

### 角色基类：继承 `<Role>BaseTest`

class 级共享 `self.<role>_page`（已登录），子类通过额外 class-scope fixture 导航到目标页面。**禁止**在用例里重复写 token 登录或手动 override `_login_setup`。

```python
@allure.feature("<角色>端主流程")
class Test<Role>Flow(<Role>BaseTest):
    @allure.story("登录 → 首页")
    def test_xxx(self):
        home = SomeHomePage(self.<role>_page)
        assert home.is_page_loaded(), "首页加载失败"
```

跨用例共享逻辑优先加到基类或派生子基类，不要在每个用例里复制。

**禁止**在某角色 class 内跳回其他角色域名（见 [browser-context.md](../playwright/browser-context.md)）。

---

## 用例书写约定

- Allure 装饰器：类级别 `@allure.feature("模块名")`，方法级别 `@allure.story("功能点")`
- 断言失败信息必须**中文**；每步跳转后先 `assert page_obj.is_page_loaded(), "...加载失败"`
- 跨 tab 场景由 PageObject 方法返回新 `Page`，用例拿到后实例化对应 PageObject
- 禁止 `time.sleep()`（阻塞 Python 进程，Playwright 无法在此期间执行任何操作）；SPA 菜单/Tab 切换后的异步渲染等待用 `page.wait_for_timeout()`（Playwright 内部等待，浏览器事件循环仍在运行）；详见 [timeout-and-wait.md](../playwright/timeout-and-wait.md)

---

## 同构元素数据驱动模式

当 ≥3 个结构相同的 UI 元素（Tab / 菜单项 / 卡片）需要逐一验证时，用**数据驱动循环 + `allure.step`** 而非 N 个独立 test 方法：

```python
@allure.story("描述覆盖范围")
def test_all_xxx(self):
    items = [("元素A", "is_a_loaded", "A 未加载"), ("元素B", "is_b_loaded", "B 未加载")]
    for name, check_method, fail_msg in items:
        with allure.step(f"点击 [{name}] 并验证"):
            assert getattr(page_obj, check_method)(), fail_msg
```

验证逻辑差异大时改用独立 test 方法。

---

## 新增测试检查清单

1. 继承角色对应的 `<Role>BaseTest`，未重复写登录
2. 所有 PageObject 有 `is_page_loaded()` 且在用例中断言
3. `pages/__init__.py` 已导出新 PageObject
4. 类有 `@allure.feature`，方法有 `@allure.story`；断言信息中文
5. 未跳回其他角色域名
6. 已在真实环境跑通：`pytest tests/<path>.py --env=<pre|prod> -v -k <case>`
7. 对应角色的 `docs/pages-catalog.md` / `docs/regression-points.md` 已同步更新

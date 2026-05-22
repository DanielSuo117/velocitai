---
name: architecture
description: POM 分层与 context 共享决策树。触发：架构、分层、POM、Page Object、基类设计、新增角色。
---

# 架构决策 — POM 分层与 context 共享模式

## 适用场景

- 新增角色/端时决定是否引入新基类
- 判断某组用例要不要共享 page / context
- 给新成员解释 POM 分层

---

## POM 分层通用骨架

```
┌─────────────────────────────────────────────┐
│                  tests/ 测试层                │
│  按角色拆分文件：test_<role>_flow.py          │
│  每个测试类继承 Base（或 Role-Base）           │
├─────────────────────────────────────────────┤
│                  pages/ 页面对象层             │
│  Base ← Login ← Landing ← Detail / ...        │
│  通用 Role 用前缀命名：Role<Role><Page>Page   │
├─────────────────────────────────────────────┤
│                  config/ 配置层                │
│  URL、Token、浏览器参数按环境切换              │
├─────────────────────────────────────────────┤
│                  conftest.py Fixture 层        │
│  browser → context → page → Role-specific base │
└─────────────────────────────────────────────┘
```

**数据流向**：`config` → `conftest`（读取配置创建 fixture） → `pages`（接收 page 对象） → `tests`（组合页面对象执行断言）

---

## PageObject 骨架

```python
# 页面名称：<中文名>
from pages.base_page import BasePage


class <PageName>(BasePage):
    # 定位符常量（类顶部）
    <LOCATOR_CONSTANT> = "<selector>"   # P<0-5>: 说明
    PAGE_IDENTIFIER = "<selector>"      # 页面加载锚点

    # 业务方法（前缀：click_ / fill_ / select_ / get_xxx_text / wait_for_ / is_xxx_visible）
    def click_<action>(self):
        self.click(self.<LOCATOR_CONSTANT>)

    # 页面加载验证（必须实现，放在最后）
    def is_page_loaded(self) -> bool:
        return self.is_visible(self.PAGE_IDENTIFIER)
```

---

## context 共享模式决策树

```
一组用例是否满足以下 3 条？
   1. 同一域名（不跨端）
   2. 有统一前置（登录、角色切换…）
   3. 有统一起点页面（可复位）
       │
       ├─ 是（三条全满足）
       │    └→ class 级共享 context
       │       - 用 scope="class" 的 page fixture（实现见 browser-config skill）
       │       - 专用基类：class setup 完成前置；function-scope autouse 复位起点
       │       - 用例末尾必须往返闭合（见 case-round-trip skill）
       │
       └─ 否（任一不满足）
            └→ function 级独立 context
               - 每用例独立 browser.new_context() + new_page()
               - 每用例独立登录
```

**注意事项：**

- ❌ 禁止 session 级跨 class 共享 context（跨 class 职责边界不清）
- ❌ 禁止同一 class 内跨域（会污染共享 context）
- 详细规则见 [rules/playwright/browser-context.md](../../rules/playwright/browser-context.md) "浏览器上下文"段

---

## 同 class 内跨用例 page 接力模式

**场景**：同一 class 的多个用例形成**线性流程链**，后一个用例的起点是前一个用例的终点，不必从头登录。

```
test_a（搜索课程）
    ↓ 页面停留在搜索结果
test_b（点击课程 → 新 tab 打开课程首页）
    ↓ 新 tab 保存为 class 属性
test_c（在课程首页继续操作）
    ↓ 直接使用 class 属性中的 page
```

### 实现要点

1. **class-scope fixture 完成一次性登录**：覆盖父类 `_login_setup` 为 no-op，用 `class_page` + `request.cls.page` 共享
2. **用例间 page 接力**：当用例打开新 tab 时，将新 page 保存到 class 属性（`type(self).<attr> = new_page`），后续用例通过 `self.<attr>` 访问
3. **新 tab 不关闭**：接力链中的 page 保持打开，直到 class 结束 context 自动销毁
4. **用例顺序即流程顺序**：pytest 默认按文件中方法出现顺序执行

### 骨架

> `class_page` fixture 的实现见 [browser-config](../browser-config/SKILL.md) "Fixture 分层模板"。

```python
class TestSomeFlow(BaseTest):

    @pytest.fixture(autouse=True)
    def _login_setup(self):
        yield  # no-op，覆盖父类

    @pytest.fixture(scope="class", autouse=True)
    def _shared_setup(self, class_page, token, request):
        login_page = LoginPage(class_page)
        login_page.login_with_token(BASE_URL, token)
        request.cls.page = class_page

    def test_step_1(self):
        ...  # self.page 已由 _shared_setup 注入，class 级共享

    def test_step_2(self):
        new_page = some_page.click_open_new_tab()
        type(self).detail_page = new_page  # 保存到 class 属性供后续用例

    def test_step_3(self):
        detail = SomeDetailPage(self.detail_page)  # 直接接力
        ...
```

### 适用条件

- ✅ 同一 class 内、用例具有明确的先后依赖关系
- ✅ 新 tab 仍在同域或已携带认证（无需二次登录）
- ❌ 如果用例间无依赖关系，不要用接力模式（改用独立 function-scope page）

---

## 新增 Role 的落地步骤

1. 决策：用上面的决策树判断新 Role 的用例是否可共享 context
2. PageObject：以 `Role<Role><Page>Page` 命名、`role_<page>` 文件名前缀，继承 `BasePage`
3. 基类（若采用 class 级共享）：新建 `tests/<role>/<role>_base_test.py::<Role>BaseTest` 继承 `BaseTest`，实现登录 + 切换 + 起点断言
4. 用例：`tests/<role>/test_<role>_flow.py::Test<Role>Flow` 继承新基类
5. 文档：在 [docs/architecture.md](../../../docs/architecture.md) 表中追加一行
6. 目录：`pages/__init__.py` 追加新页面导出

---

## 决策落地参考

本项目当前的落地情况（具体类名、fixture、起点页面）→ [docs/architecture.md](../../../docs/architecture.md)。

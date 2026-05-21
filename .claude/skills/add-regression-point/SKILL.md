---
name: add-regression-point
description: 为已有 PageObject 增量添加回归测试点。触发：新增测试点、添加回归点、add test point、增加覆盖、扩展页面方法。
---

# Add Regression Point — 新增回归测试点

## 适用场景

为**已有 PageObject** 新增单个或多个回归测试点。与 `gen-page-test`（新建整个页面）不同，本 skill 针对已存在的页面做**增量扩展**。

## 输入参数

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| 目标 PageObject | 是 | 已有的页面类名 | `<ExistingPage>` |
| 页面 URL | 是 | 真实可访问的页面 URL（已认证态） | https://example.com/xxx |
| 新增测试点 | 是 | 需要覆盖的交互元素 | 点击收藏、筛选类型 |

---

## 执行流程（4 步）

### Step 1：访问真实页面抽取新元素定位符

使用 agent-browser 以已认证态访问目标 URL，为每个新增测试点按 [locator-replacer](../locator-replacer/SKILL.md) 六级优先级选定定位符。浏览器工具选型遵循 [agent-behavior P0.4](../../rules/agent-behavior/agent-behavior.md)：DOM 探索 / 定位符采集用 agent-browser，agent-browser 未安装时降级到 Playwright MCP。

### Step 2：更新 PageObject

在 `pages/<page_name>_page.py` 中追加：

**2a. 新增定位符常量**（插入到已有常量之后、方法之前）

```python
    # ↓ 新增定位符（来自真实页面，<日期>）
    <NEW_LOCATOR_1> = "<真实定位符>"    # P<0-5>: 说明
    <NEW_LOCATOR_2> = "<真实定位符>"    # P<0-5>: 说明
```

**2b. 新增业务方法**（插入到 `is_page_loaded()` 之前）

```python
    def click_<new_method_1>(self):
        self.click(self.<NEW_LOCATOR_1>)

    def click_<new_method_2>(self):
        self.click(self.<NEW_LOCATOR_2>)

    def is_page_loaded(self) -> bool:    # 保持为最后一个方法
        return self.is_visible(self.PAGE_IDENTIFIER)
```

### Step 3：在对应角色回归测试中追加调用

根据目标 PageObject 的角色：
- 对应角色页面 → `tests/teacher/test_<feature>.py`（当前无主流程用例，新建时继承 `<Role>BaseTest`）
- 对应角色页面 → `tests/<role>/test_<role>_flow.py`
- 对应角色 → `tests/<role>/test_<role>_flow.py`

在对应 `@allure.story` 方法中追加：

```python
    # ↓ 新增回归点
    <page_instance>.click_<new_method_1>()
    <page_instance>.click_<new_method_2>()
```

**⚠️ 若新增测试点的跳转目标脱离门户布局**（例如离开侧边导航的子路由、沉浸式页面），必须套用 [case-round-trip](../case-round-trip/SKILL.md)：PageObject 提供 `click_back_to_<landing>`，用例末尾显式返回起点页并断言；否则后续用例复位 fixture 会超时。

### Step 4：同步更新 `docs/`

- 在对应角色的 pages-catalog 子文件中追加新方法行：
  - 对应角色 → [pages-catalog.md](../../../docs/pages-catalog.md)
  - （同上）
  - 
- 在对应角色的 regression-points 子文件中追加回归点行 + 关键定位符常量：
  - 对应角色 → [regression-points.md](../../../docs/regression-points.md)
  - 

---

## 检查清单

通用检查（命名/导入/is_page_loaded/allure）→ coding-conventions.md "新增测试检查清单"

- [ ] 新增定位符均来自真实页面 DOM，行尾标注 P0~P5 级别
- [ ] 对应角色 `test_<role>_flow.py` 已追加新方法调用
- [ ] 对应角色的 `docs/pages-catalog-<role>.md` 已同步
- [ ] 对应角色的 `docs/regression-points-<role>.md` 已同步
- [ ] 若跳转目标脱离门户布局，已套用 `case-round-trip`

## 注意事项

- **不要修改已有方法**，只做增量添加
- **不需要更新** `pages/__init__.py`（页面类已存在）
- 如果新增测试点需要页面导航（跳转到子页面），考虑新建独立 PageObject（使用 `gen-page-test`）
- 定位符直接基于真实页面抽取，不使用占位符

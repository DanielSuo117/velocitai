---
name: gen-page-test
description: 一键生成 PageObject + 配套测试。触发：新增页面、生成页面、gen page、create page、添加页面对象。
---

# Gen Page Test — 一键生成 PageObject + 测试

## 使用方式

```
用户输入：为 <中文页面名>（URL: https://...）生成页面对象和测试，测试点：点击A、填写B、查看C
```

## 输入参数

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| 页面名称 | 是 | 中文业务名称 | 课程管理页 |
| 页面 URL | 是 | 真实可访问的页面 URL（已认证态） | https://example.com/xxx |
| 角色 | 是 | 项目中已有的角色（如 `<role>`） | 对应角色 |
| 类名 | 否（自动推导） | PascalCase | `<Role><Page>Page` |
| 回归测试点 | 是 | 需要覆盖的交互元素 | 点击新建、搜索、删除 |

**类名推导规则**：
- 非特定角色：中文名 → 英文翻译 → PascalCase + `Page` 后缀（如 `<Feature>Page`）
- 特定角色：`<Role>` + 英文翻译 → PascalCase + `Page` 后缀（如 `<Role><Feature>Page`）
- 角色文件名前缀：`<role>_`（如 `<role>_<feature>_page.py`）

项目中已有的具体类名清单见 [docs/pages-catalog.md](../../../docs/pages-catalog.md)。

---

## 执行流程（6 步）

### Step 1：访问真实页面获取 DOM

`browser_navigate`（必要时先 `/entry?token=xxx`）→ `browser_snapshot` → `browser_evaluate` 提取元素。按 [locator-replacer](../locator-replacer/SKILL.md) 六级优先级（P0 → P5）选出稳定定位符。

### Step 2：生成 PageObject 文件

创建 `pages/<snake_name>_page.py`：

```python
# 页面名称：<中文名>
from pages.base_page import BasePage


class <ClassName>(BasePage):
    # 定位符 — 来自真实页面（<日期>，URL: <页面URL>）
    <LOCATOR_1> = "<真实定位符>"    # P<0-5>: 说明
    <LOCATOR_2> = "<真实定位符>"    # P<0-5>: 说明
    PAGE_IDENTIFIER = "<页面标识定位符>"    # P<0-5>: 说明

    def click_<method_1>(self):
        self.click(self.<LOCATOR_1>)

    def click_<method_2>(self):
        self.click(self.<LOCATOR_2>)

    def is_page_loaded(self) -> bool:
        return self.is_visible(self.PAGE_IDENTIFIER)
```

### Step 3：更新 `pages/__init__.py`

```python
from pages.<snake_name>_page import <ClassName>

# 在 __all__ 列表中追加 "<ClassName>"
```

### Step 4：在对应角色测试文件追加 story

目标文件：对应角色 `tests/<role>/test_<role>_flow.py`（继承 `<Role>BaseTest`）中的 `Test<Role>Flow` 类。

对应角色示例：

```python
@allure.story("<页面中文名>")
def test_<snake_name>(self):
    page_obj = <ClassName>(self.<role>_page)
    self.<role>_page.goto("<页面URL>")
    assert page_obj.is_page_loaded(), "<页面中文名>加载失败"
    page_obj.click_<method_1>()
    ...
```

对应角色使用 `self.<role>_page`，且若脱离门户布局须往返闭合（见 case-round-trip）：

```python
@allure.story("<页面中文名>")
def test_<snake_name>(self):
    self.<role>_home.click_<navigation>()
    page_obj = <ClassName>(self.<role>_page)
    assert page_obj.is_page_loaded(), "<页面中文名>加载失败"
    page_obj.click_<method_1>()
    page_obj.click_back_to_<landing>()
    assert self.<role>_home.is_page_loaded(), "返回起点失败"
```

### Step 5：真实环境验证

```bash
pytest tests/<role>/test_<role>_flow.py --env=<pre|prod> -v -k "test_<snake_name>"
```

**⚠️ 运行前向用户确认 `--env`**（见 [agent-behavior.md](../../rules/agent-behavior/agent-behavior.md) P0.2）。

失败时 → [locator-replacer](../locator-replacer/SKILL.md) 重新抽取定位符，或 [test-runner](../test-runner/SKILL.md) 分析失败类型。

### Step 6：同步更新 `docs/`

- `docs/pages-catalog.md`：追加新页面类 + 方法表
- `docs/regression-points.md`：追加回归点表 + 关键定位符段

---

## 生成后检查清单

通用检查（命名/导入/is_page_loaded/allure）→ coding-conventions.md "新增测试检查清单"

- [ ] 定位符均来自真实页面 DOM，行尾标注 P0~P5 级别
- [ ] `pytest tests/<role>/test_<role>_flow.py --env=<pre|prod> -v -k "test_<name>"` 通过
- [ ] 对应角色的 `docs/pages-catalog.md` 已追加
- [ ] 对应角色的 `docs/regression-points.md` 已追加
- [ ] 若跳转目标脱离门户布局，已套用 [case-round-trip](../case-round-trip/SKILL.md)

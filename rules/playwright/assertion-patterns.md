---
paths:
  - "pages/**"
  - "tests/**"
---

# 断言模式

**触发**：编写 `is_page_loaded()` / `wait_for_element` 目标、或对操作结果做断言时。

---

## 等待目标唯一性

`wait_for_element` / `is_page_loaded` 的定位符必须是**目标页面独有的**；在来源页面执行 `locator.count()` 必须为 0。

❌ 反例：

```python
# 配置页标题含「<配置页标题>」，结果页标题也含同名子串
RESULT_HEADER = "text=<配置页标题>"
def wait_for_generation(self):
    self.wait_for_element(self.RESULT_HEADER)   # 在配置页就立即满足
```

✅ 正例：

```python
RESULT_UNIQUE_FLAG = "text=<结果页独有标识>"  # 仅结果页才有
def wait_for_generation(self):
    self.wait_for_element(self.RESULT_UNIQUE_FLAG)
```

---

## Toast 断言：优先用持久 UI 状态变更

Toast 只显示 2-3 秒，`is_visible` 可能在 toast 消失后才检查。按钮文案变更是持久状态，更可靠。

❌ 反例：

```python
def is_add_success(self) -> bool:
    return self.is_visible("text=保存成功", timeout=10000)   # toast 可能已消失
```

✅ 正例：

```python
ADDED_BTN = "text=已添加"
SUCCESS_TOAST = "text=保存成功"
def is_add_success(self) -> bool:
    return (
        self.is_visible(self.ADDED_BTN, timeout=10000)       # 优先：持久状态
        or self.is_visible(self.SUCCESS_TOAST, timeout=3000)  # 辅助：toast
    )
```

### Toast 时序陷阱

保存方法只等 `networkidle`，不加额外 `wait_for_timeout`。让调用方立即检测 Toast。

完整模式（含反例/正例/重定向/数据对比）→ [save-verify-strategy skill](../../skills/save-verify-strategy/SKILL.md)

---

## 断言目标稳定性

断言目标必须选**模板级文本**（不随业务数据变化），禁止选数据依赖的内容。

| 稳定性 | 定义 | 能否用于断言 | 示例 |
|--------|------|-------------|------|
| **模板级** | 页面框架自带的标题/标签，所有同类页面均一致 | ✅ 首选 | 页面固定标题、Tab 标签名 |
| **配置级** | 管理员配置但不频繁变化 | ⚠️ 仅辅助 | 项目名称 |
| **数据级** | 随用户操作/时间变化的动态数据 | ❌ 禁止 | 动态计数 "116" |

**检查清单**：
1. 该文本是否在所有同类页面中都出现？是 → 模板级，可用
2. 该文本是否会因数据更新而变化？是 → 数据级，禁止
3. 该文本是否可能与其他区域重名？是 → 用 CSS scope 限定

❌ 反例：

```python
ITEM_COUNT = "text=116"                    # 数据级，编辑后数值变化
```

✅ 正例：

```python
MODULE_GOAL = "text=<模板级标签>"          # 模板级
SECTION_HEADER = "css=.section-wrapper-header >> text=<模板级名称>"  # scope 避免重名
```

---

## 页面加载 + 接口错误：必须合并断言，禁止先后分步

当用例同时验证「页面渲染」和「接口无报错」时，**禁止**先 `assert is_loaded()` 再 `get_api_errors()`。
若接口 500 导致页面白屏，`is_loaded()` 先失败，测试报告只显示"元素未显示"，丢失真正的根因（哪个接口挂了）。

**规则**：使用 `BaseTest.assert_page_and_api()` 一步完成。该方法先收集接口错误写入报告，再断言页面加载。
页面加载失败时，接口错误信息会追加到失败消息中。

❌ 反例：

```python
# 接口 500 → 页面白屏 → is_loaded() 失败 → 停在这里
# → 永远不会执行 get_api_errors() → 报告里看不到是哪个接口挂了
with allure.step("验证页面加载完成"):
    assert page.is_xxx_loaded(), "页面加载失败"

with allure.step("检查接口是否有报错"):
    api_errors = page.get_api_errors()
    if api_errors:
        assert False, f"存在接口错误：..."
```

✅ 正例：

```python
with allure.step("验证页面加载及接口状态"):
    self.assert_page_and_api(
        page, "is_xxx_loaded",
        "页面名称", "页面加载失败：具体描述",
    )
```

**`assert_page_and_api` 签名**（定义在 `tests/base_test.py::BaseTest`）：

```python
@staticmethod
def assert_page_and_api(page_obj, is_loaded_method: str, page_name: str, load_fail_msg: str):
```

- `page_obj`：PageObject 实例（必须继承 `BasePage`，`get_api_errors()` 已提升到 `BasePage`）
- `is_loaded_method`：字符串形式的方法名，如 `"is_target_page_loaded"`
- `page_name`：中文页面名，用于接口错误报告标题
- `load_fail_msg`：页面加载失败时的断言消息

**适用范围**：所有同时需要验证页面渲染 + 接口状态的用例（含 Tab 切换 + 接口检查的场景）。

---

## 白屏检测：容器存在但内容未渲染

SPA 应用中 `is_visible(容器)` 可能对空白页面返回 true（容器 div 在 DOM 中但子组件未挂载）。需额外用 JS evaluate 检查内容区域是否有子元素。

详细模式与反例/正例 → [page-load-assertion skill](../../skills/page-load-assertion/SKILL.md) 模式 E

---

## Performance API 跨用例隔离

`get_api_errors()` 基于 `performance.getEntriesByType('resource')` 收集接口错误。在 class 级共享 context 中，不清空缓冲区会导致前面用例的错误污染后续用例（单独跑通过、批量跑失败）。

规则：收集后必须 `performance.clearResourceTimings()` → [performance-api-isolation.md](./performance-api-isolation.md)

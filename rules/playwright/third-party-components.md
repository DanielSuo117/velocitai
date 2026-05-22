---
paths:
  - "pages/**"
---

# 第三方组件交互

**触发**：操作 Arco Design / Element Plus / Ant Design 等组件库的 Select / TreeSelect 下拉框后需要关闭它。

**规则**：`keyboard.press("Escape")` 对组件库下拉框不可靠（框架内部拦截事件）。关闭下拉框必须改用点击页面其他可见元素（如页面标题、表单标签），触发 blur 事件收起下拉框。

❌ 反例：

```python
def select_option(self, name: str):
    self.click(self.SELECT_INPUT)
    self.click(f"css=.popup >> text={name}")
    self.page.keyboard.press("Escape")       # 组件库 TreeSelect 不响应 Escape → 下拉框仍在
```

✅ 正例：

```python
def select_option(self, name: str):
    self.click(self.SELECT_INPUT)
    self.click(f"css=.popup >> text={name}")
    self.click(self.PAGE_TITLE)               # 点击页面其他元素，触发 blur → 下拉框收起
    self.page.wait_for_timeout(1000)
```

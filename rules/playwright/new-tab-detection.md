---
paths:
  - "pages/**"
---

# 新 tab 检测

**触发**：编写涉及页面跳转的 PageObject 方法时。

**规则**：编码前必须用 `agent-browser click @ref` + `agent-browser tab list` 确认点击是同 tab 导航还是新 tab。若是新 tab，PageObject 方法必须用 `context.expect_page()` 捕获并返回新 page。

❌ 反例：

```python
def click_generate(self):
    self.click(self.GENERATE_BTN)
    # 假设是同 tab SPA 跳转 → 实际打开了新 tab → 90 秒超时
```

✅ 正例：

```python
def click_generate(self):
    with self.page.context.expect_page() as new_page_info:
        self.click(self.GENERATE_BTN)
    new_page = new_page_info.value
    new_page.wait_for_load_state("networkidle")
    return new_page
```

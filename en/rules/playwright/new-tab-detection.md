---
paths:
  - "pages/**"
---

# New Tab Detection

**Trigger**: Writing PageObject methods that involve page navigation.

**Rule**: Before coding, use `agent-browser click @ref` + `agent-browser tab list` to confirm whether a click is a same-tab navigation or a new tab. If it's a new tab, the PageObject method must use `context.expect_page()` to capture and return the new page.

❌ Anti-pattern:

```python
def click_generate(self):
    self.click(self.GENERATE_BTN)
    # Assumes same-tab SPA navigation → actually opens a new tab → 90-second timeout
```

✅ Best practice:

```python
def click_generate(self):
    with self.page.context.expect_page() as new_page_info:
        self.click(self.GENERATE_BTN)
    new_page = new_page_info.value
    new_page.wait_for_load_state("networkidle")
    return new_page
```

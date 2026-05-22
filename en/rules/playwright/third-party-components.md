---
paths:
  - "pages/**"
---

# Third-Party Component Interactions

**Trigger**: After operating on Select / TreeSelect dropdowns from component libraries like Arco Design / Element Plus / Ant Design and needing to close the dropdown.

**Rule**: `keyboard.press("Escape")` is unreliable for component library dropdowns (the framework intercepts the event internally). To close a dropdown, click on another visible element on the page (e.g. page title, form label) instead, triggering a blur event to collapse the dropdown.

❌ Anti-pattern:

```python
def select_option(self, name: str):
    self.click(self.SELECT_INPUT)
    self.click(f"css=.popup >> text={name}")
    self.page.keyboard.press("Escape")       # component library TreeSelect doesn't respond to Escape → dropdown stays open
```

✅ Best practice:

```python
def select_option(self, name: str):
    self.click(self.SELECT_INPUT)
    self.click(f"css=.popup >> text={name}")
    self.click(self.PAGE_TITLE)               # click another element on the page, triggers blur → dropdown collapses
    self.page.wait_for_timeout(1000)
```

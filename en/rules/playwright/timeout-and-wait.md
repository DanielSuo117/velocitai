---
paths:
  - "pages/**"
  - "tests/**"
  - "conftest.py"
---

# Timeout Triage & Wait Strategy

---

## I. Timeout Failure Triage: Confirm "Which Page" First, Then Investigate "Whether Locator Is Correct"

**Trigger**: `wait_for_element` / `is_visible` / `inner_text` and similar operations report `TimeoutError`.

**Rule**: On a timeout failure, the **first step** is always to confirm which page the current page object is pointing to. **Forbidden** to jump straight to changing the locator.

90% of timeout issues are not "element not found" but "not on the target page at all". Common causes:
1. A button opened a **new tab** and the code is still waiting on the old tab's page object (most common)
2. SPA route did not navigate (previous step was blocked by a dropdown/dialog, click did not take effect)
3. Page was redirected to login page (token expired, cross-domain auth failed)

**Investigation order (must follow strictly):**

```
TimeoutError
   │
   ▼
① Print page.url and page.title()
   │  → URL wrong → page didn't navigate; investigate if previous click took effect
   │  → URL correct → proceed to ②
   ▼
② Check if a new tab opened (change in context.pages count)
   │  → New tab appeared → target content is in the new tab, current page is the old one
   │  → No new tab → proceed to ③
   ▼
③ Only now investigate locator issues (page.locator("xxx").count())
```

❌ Anti-pattern: Change locators on every timeout; change 4 times and all timeout; root cause is new tab.

✅ Best practice:

```python
print(f"Current URL: {page.url}")
print(f"Current title: {page.title()}")
print(f"Number of pages in context: {len(page.context.pages)}")
```

---

## II. Wait Strategy

**Trigger**: Writing fixture / PageObject code involving page navigation or SPA module switch wait logic.

**Rule**: Global implicit wait + explicit timeout only for slow paths. Full strategy → [wait-strategy skill](../../skills/wait-strategy/SKILL.md)

### After SPA Menu/Tab Switch, `networkidle` Does Not Equal Render Complete

In SPA frameworks like Vue / React, after clicking a menu to switch modules, `networkidle` only guarantees network requests are complete — **it cannot guarantee components are rendered into the DOM**.

**Rule**: After SPA menu/tab switch, if the next step depends on newly rendered elements, must add `wait_for_timeout(3000)` or `wait_for_element()` after `networkidle` to confirm stability.

❌ Anti-pattern:

```python
def _setup_context(self, ...):
    home.click_target_menu()
    assert home.is_target_section_visible()
    home.search("<search keyword>")               # search box is being re-rendered by Vue
```

✅ Best practice:

```python
def _setup_context(self, ...):
    home.click_target_menu()
    assert home.is_target_section_visible()
    self.<role>_page.wait_for_timeout(3000)   # wait for async component to finish rendering
    home.search("<search keyword>")
```

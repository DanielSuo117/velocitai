---
name: case-round-trip
description: Under a shared page, a test case that leaves the start page must return via the UI and assert. Trigger: round-trip closure, case round trip, reset timeout, scope shared page.
---

# Case Round Trip — Test Case Round-Trip Closure

> Applicable to Playwright + pytest only.

## Core Rule

Under a shared page (fixture with scope > function), **a test case that leaves the start page must return via the real UI at the end and assert**; do not use `goto` as a fallback in the reset fixture.

## When It Applies

- Multiple test cases share a single page / browser context (class/module/session scope)
- A test case enters a page that "leaves the portal layout" (sub-route, immersive page, cross-subdomain)
- The reset fixture relies on elements that only exist in the portal layout (sidebar / top nav)

## How To Do It

1. Add `click_back_to_<landing>()` to each PageObject that "leaves the portal layout", using the real UI back button
2. After the main assertion, explicitly call the return method and assert the start page is loaded again
3. Keep the reset fixture in its simplest form (only portal navigation), no `goto` fallback

```python
def test_enter_detail(self):
    self.home.click_first_item()
    detail = DetailPage(self.page)
    assert detail.is_page_loaded(), "Detail page failed to load"

    detail.click_back_to_home()
    assert self.home.is_page_loaded(), "Failed to return to start page"
```

## Strict Criteria for Start Page is_page_loaded

The reset fixture usually checks `if not start.is_page_loaded(): start.click_back_to_landing()`. If `is_page_loaded()` only verifies "page skeleton is visible" (title / container), the skeleton remains visible after switching to another tab/sub-route → returns True → reset never triggers → next test case starts at wrong position.

**Rule: The start PageObject's `is_page_loaded()` must include "currently at start state" criteria** (start tab active state / start URL / start-unique content), not just "skeleton exists".

```python
# ❌ Only checks skeleton — still returns True after switching to another tab, reset fails
def is_page_loaded(self) -> bool:
    return self.is_visible(self.PAGE_TITLE) and self.is_visible(self.TAB_BAR)

# ✅ Add "currently on start tab" criterion — returns False after tab switch, triggering reset
def is_page_loaded(self) -> bool:
    return (
        self.is_visible(self.PAGE_TITLE)
        and self.is_visible(self.TAB_BAR)
        and self.is_visible(self.LANDING_TAB_ACTIVE_MARK)   # key 3rd condition
    )
```

The `LANDING_TAB_ACTIVE_MARK` selector must use `text=` or similar to lock onto the **specific start tab** (e.g. `.tab.active >> text=<start tab name>`), otherwise `.active` will match any currently active tab, causing the same failure (see [locator-strategy.md state-class selector must be anchored with text](../../rules/playwright/locator-strategy.md)).

## Decision

```
Does the navigation target still retain the start page's portal navigation?
├─ Yes → rely on reset fixture
└─ No → PageObject must provide return method + test case explicitly returns + assertion
```

## ❌ Anti-Patterns

- Enter an immersive page, only assert the entry, don't return → subsequent test cases' reset fixture can't click portal navigation
- `page.goto(<landing_url>)` bypasses the back button → loses regression coverage of the back button
- `if not visible: goto(...)` put in reset fixture → masks the real problem of "test case not closed"

## Checklist

- [ ] Navigation target leaves portal layout → this rule applies
- [ ] PageObject provides `click_back_to_<landing>()`
- [ ] Test case calls return method at the end and asserts start page loaded
- [ ] Tests still pass when execution order is scrambled

---

## Project Implementation Reference

For PageObjects in the project that leave the portal layout (need to implement `click_back_to_<landing>`), see [docs/pages-catalog.md](../../../docs/pages-catalog.md) and [docs/regression-points.md](../../../docs/regression-points.md) (pages marked with "⚠️ Navigation target leaves portal layout").

---
paths:
  - "pages/**"
  - "tests/**"
---

# Assertion Patterns

**Trigger**: Writing `is_page_loaded()` / `wait_for_element` targets, or asserting on operation results.

---

## Wait Target Uniqueness

The locator for `wait_for_element` / `is_page_loaded` must be **unique to the target page**; running `locator.count()` on the source page must return 0.

❌ Anti-pattern:

```python
# Config page title contains "<config page title>"; result page title also contains the same substring
RESULT_HEADER = "text=<config page title>"
def wait_for_generation(self):
    self.wait_for_element(self.RESULT_HEADER)   # immediately satisfied on config page
```

✅ Best practice:

```python
RESULT_UNIQUE_FLAG = "text=<result page unique identifier>"  # only present on result page
def wait_for_generation(self):
    self.wait_for_element(self.RESULT_UNIQUE_FLAG)
```

---

## Toast Assertions: Prefer Persistent UI State Changes

Toast only displays for 2-3 seconds; `is_visible` may check after the toast has disappeared. A button text change is a persistent state — more reliable.

❌ Anti-pattern:

```python
def is_add_success(self) -> bool:
    return self.is_visible("text=Saved successfully", timeout=10000)   # toast may have disappeared
```

✅ Best practice:

```python
ADDED_BTN = "text=Added"
SUCCESS_TOAST = "text=Saved successfully"
def is_add_success(self) -> bool:
    return (
        self.is_visible(self.ADDED_BTN, timeout=10000)       # preferred: persistent state
        or self.is_visible(self.SUCCESS_TOAST, timeout=3000)  # supplementary: toast
    )
```

### Toast Timing Trap

The save method only waits for `networkidle`, no extra `wait_for_timeout`. Let the caller detect Toast immediately.

Full pattern (with anti-pattern/best practice/redirect/data comparison) → [save-verify-strategy skill](../../skills/save-verify-strategy/SKILL.md)

---

## Assertion Target Stability

Assertion targets must use **template-level text** (does not vary with business data); forbidden to use data-dependent content.

| Stability | Definition | Can Use for Assertion | Example |
|--------|------|-------------|------|
| **Template-level** | Titles/labels built into the page frame, consistent across all pages of this type | ✅ Preferred | Fixed page title, tab label name |
| **Config-level** | Configured by admin but does not change frequently | ⚠️ Supplementary only | Project name |
| **Data-level** | Dynamic data that changes with user operations/time | ❌ Forbidden | Dynamic count "116" |

**Checklist:**
1. Does this text appear on all pages of this type? Yes → template-level, usable
2. Will this text change due to data updates? Yes → data-level, forbidden
3. Can this text clash with other areas? Yes → use CSS scope to limit

❌ Anti-pattern:

```python
ITEM_COUNT = "text=116"                    # data-level, value changes after editing
```

✅ Best practice:

```python
MODULE_GOAL = "text=<template-level label>"          # template-level
SECTION_HEADER = "css=.section-wrapper-header >> text=<template-level name>"  # scope prevents name clash
```

---

## Page Load + API Error: Must Assert Together, Forbidden to Split into Two Steps

When a test case simultaneously verifies "page rendered" and "no API errors", **forbidden** to `assert is_loaded()` first and then `get_api_errors()`.
If an API 500 causes a blank screen, `is_loaded()` fails first, the test report only shows "element not visible", losing the true root cause (which API failed).

**Rule**: Use `BaseTest.assert_page_and_api()` to complete both in one step. This method collects API errors and writes them to the report first, then asserts page load.
When page load fails, API error information is appended to the failure message.

❌ Anti-pattern:

```python
# API 500 → blank screen → is_loaded() fails → stops here
# → get_api_errors() never executes → report doesn't show which API failed
with allure.step("Verify page load complete"):
    assert page.is_xxx_loaded(), "Page failed to load"

with allure.step("Check API errors"):
    api_errors = page.get_api_errors()
    if api_errors:
        assert False, f"API errors exist: ..."
```

✅ Best practice:

```python
with allure.step("Verify page load and API status"):
    self.assert_page_and_api(
        page, "is_xxx_loaded",
        "Page Name", "Page failed to load: specific description",
    )
```

**`assert_page_and_api` signature** (defined in `tests/base_test.py::BaseTest`):

```python
@staticmethod
def assert_page_and_api(page_obj, is_loaded_method: str, page_name: str, load_fail_msg: str):
```

- `page_obj`: PageObject instance (must inherit `BasePage`; `get_api_errors()` is already promoted to `BasePage`)
- `is_loaded_method`: method name as a string, e.g. `"is_target_page_loaded"`
- `page_name`: page name in English, used for API error report title
- `load_fail_msg`: assertion message when page fails to load

**Applicable scope**: All test cases that need to verify both page rendering + API status (including scenarios with tab switching + API checking).

---

## Blank Screen Detection: Container Exists But Content Not Rendered

In SPA applications, `is_visible(container)` may return true for a blank page (container div is in DOM but child components not mounted). Need to additionally use JS evaluate to check if the content area has child elements.

Detailed patterns with anti-patterns/best practices → [page-load-assertion skill](../../skills/page-load-assertion/SKILL.md) Mode E

---

## Performance API Cross-Test Isolation

`get_api_errors()` is based on `performance.getEntriesByType('resource')` to collect API errors. In a class-level shared context, not clearing the buffer will cause errors from earlier tests to contaminate subsequent tests (passes when run individually, fails when run in batch).

Rule: must call `performance.clearResourceTimings()` after collection → [performance-api-isolation.md](./performance-api-isolation.md)

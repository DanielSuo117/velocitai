---
name: wait-strategy
description: Implicit wait as default, explicit wait only for slow paths. Trigger: wait strategy, timeout, wait, implicit wait, explicit wait.
---

# Wait Strategy — Implicit Wait Primary, Explicit Wait Secondary

## Core Principle

**Implicit wait covers 99% of scenarios; explicit wait is only used for known slow paths.**

---

## I. Implicit Wait (Default, Globally Effective)

### What is Implicit Wait

Set via `page.set_default_timeout(ms)` immediately after page creation. After that, all Playwright operations on that page (`click`, `fill`, `locator.wait_for`, `is_visible`, etc.) automatically wait for element readiness, retrying continuously before timeout — no need to specify timeout individually for each call.

### Configuration Location

The implicit wait timeout duration is declared centrally in the config file (e.g. `DEFAULT_TIMEOUT` constant), and injected into each page instance in the fixture layer:

```python
# Config file
DEFAULT_TIMEOUT = 15000   # 15 seconds, tolerates network fluctuations

# Fixture layer (set for both function-level and class-level)
page = context.new_page()
page.set_default_timeout(DEFAULT_TIMEOUT)
```

### Recommended Duration

| Environment | Recommended | Notes |
|------|--------|------|
| Internal network / CI | 10000 (10s) | Stable network, no need for long waits |
| External network / production | 15000 (15s) | Tolerates occasional network fluctuations |
| Weak network testing | 20000~30000 | Specialized weak network scenarios |

---

## II. Explicit Wait (Only for Special Scenarios)

### When to Use

| Scenario | Reason | Approach |
|------|------|------|
| Large file upload / import | Server processing takes much longer than typical page operations | `self.is_visible(LOCATOR, timeout=60000)` |
| Long polling / async task callback | Backend processing completes before frontend state refreshes | `page.locator(...).wait_for(state="visible", timeout=30000)` |
| Third-party service redirect | OAuth / payment etc. external page response is unpredictable | `page.wait_for_url("**/callback**", timeout=30000)` |
| First cold start | Service just deployed, first request is slow | Increase timeout individually for the first navigation |

### Usage

Pass an explicit timeout at the **call site**, overriding the implicit default:

```python
# BasePage wrapper method supports timeout parameter
def is_visible(self, locator, timeout=DEFAULT_TIMEOUT) -> bool:
    ...

# In test case: only specify explicitly for known slow operations
def test_upload_large_file(self):
    self.page_obj.click_upload()
    assert self.page_obj.is_visible(
        self.page_obj.UPLOAD_SUCCESS_INDICATOR,
        timeout=60000   # explicit 60-second wait, only here
    ), "Large file upload timed out"
```

### Prohibited Practices

- **Forbid `time.sleep()` hard waits** — Playwright's auto-wait mechanism already covers this; hard waits waste time and are unreliable
- **Forbid adding explicit timeout to every operation** — this defeats the purpose of unified implicit wait management
- **Forbid hardcoding long timeouts inside PageObject methods** — timeout values should be decided by the caller (test layer) based on the scenario

---

## III. Relationship Between `wait_for_load_state` and Implicit Wait

`page.wait_for_load_state("networkidle")` is a **navigation-level wait**, complementary to element-level implicit wait — they don't conflict:

| Wait Type | Level | Trigger Timing | Controlled by `set_default_timeout` |
|----------|---------|---------|------------------------------|
| `wait_for_load_state` | Navigation / Network | After page jump, bulk AJAX requests | Controlled by `set_default_navigation_timeout` |
| Implicit wait | Element | Before each element operation | Yes |

Recommended pattern:

```python
def click_navigate_to_target(self):
    self.click(self.TARGET_LINK)
    self.page.wait_for_load_state("networkidle")  # wait for network requests to complete
    # subsequent is_visible / click operations are covered by implicit wait
```

---

## Checklist

- [ ] Global `DEFAULT_TIMEOUT` declared centrally in config file
- [ ] All page fixtures (function-level / class-level) call `page.set_default_timeout()`
- [ ] No `time.sleep()` in PageObject business methods
- [ ] Explicit timeout only appears at call sites for known slow paths, not inside PageObjects
- [ ] PageObject's `is_visible()` and similar methods retain a `timeout` parameter for callers to override

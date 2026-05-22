---
name: save-verify-strategy
description: Post-form-save verification (Toast / redirect / data comparison / rich-text clear). Trigger: save verification, toast, redirect detection, Meta+A, save success detection.
---

# Form Save Verification Strategy

---

## I. macOS Rich-Text Editor Select-All Must Use Meta+A

In macOS Chromium, `Control+A` is the Emacs shortcut (moves cursor to start of line), **not** "select all". In rich-text editors like CKEditor / TinyMCE / Quill, `Control+A` cannot select all content, leaving old content behind.

❌ Anti-pattern:

```python
def fill_rich_text(self, text: str):
    self.click(self.EDITOR)
    self.page.keyboard.press("Control+A")   # on macOS only moves cursor to line start
    self.page.keyboard.press("Backspace")   # only deletes one character, old content remains
    self.page.keyboard.type(text)           # new content appended after old content
```

✅ Best practice:

```python
def fill_rich_text(self, text: str):
    self.click(self.EDITOR)
    self.page.keyboard.press("Meta+A")      # macOS Command+A = select all
    self.page.keyboard.press("Backspace")   # clear all content
    self.page.keyboard.type(text)           # write fresh content
```

**Diagnostic signal**: Data entered has leftover old content at the end (e.g. `"2026-05-06 10:30:00123"` with extra `123` at the end) → select-all shortcut not working.

---

## II. Post-Save Verification Strategy: Three-Level Selection

| Post-Save Behavior | Verification Method | Reliability | Applicable Scenario |
|-----------|---------|--------|---------|
| Shows Toast | `is_visible(toast_locator)` — must detect **immediately** after networkidle | Low (disappears in 2-3s) | Scenarios with a clear Toast |
| Page redirect | Detect editing page signature element disappears `wait_for(state="hidden")` | Medium (persistent state) | Scenarios where save triggers auto-redirect |
| No UI feedback | Write marker data → reopen → read and compare | High (data-level verification) | No Toast, uncertain about redirect |

**Principle**: The three levels can be combined. Prioritize persistent state changes; Toast is supplementary only.

### 2.1 Toast Timing Trap

`wait_for_timeout()` in the `click_save()` method consumes Toast's lifetime. **Must** detect Toast immediately after networkidle — do not wait first and then detect.

❌ Anti-pattern:

```python
def click_save(self):
    self.click(self.SAVE_BTN)
    self.page.wait_for_load_state("networkidle")
    self.page.wait_for_timeout(3000)   # Toast appeared and disappeared during these 3s

# Caller
assert page.is_visible(toast)          # Toast already gone, always False
```

✅ Best practice:

```python
def click_save(self):
    self.click(self.SAVE_BTN)
    self.page.wait_for_load_state("networkidle")
    # No extra wait — let caller detect Toast immediately

# Caller
is_ok = page.is_visible(toast, timeout=10000)   # start waiting for Toast immediately
page.wait_for_timeout(3000)                      # wait for page to stabilize after detection
```

### 2.2 Redirect Detection

After saving, the page may redirect away from the editing page. Confirm save success by detecting that the editing page's **signature element disappears**:

```python
def is_save_success(self) -> bool:
    """Editing page header disappears = save successful and left editing page"""
    try:
        self.page.locator(self.EDIT_PAGE_HEADER).first.wait_for(
            state="hidden", timeout=15000
        )
        return True
    except Exception:
        return False
```

### 2.3 Redirect Destination Cannot Be Assumed

The redirect destination after saving may differ depending on **navigation context** (direct URL access vs. SPA in-app navigation vs. operation in a new tab). Do not assert a redirect to a specific page.

❌ Anti-pattern:

```python
# Assume saving always redirects to home page
redirected_home = HomePage(page)
assert redirected_home.is_page_loaded()   # may actually navigate elsewhere
```

✅ Best practice:

```python
# Only verify that we left the editing page, don't assume where we went
assert edit_page.is_save_success()        # editing page header disappears = save success
```

---

## III. Multi-Tab Post-Save: Close Old Tab, Re-Enter from Original Tab

After saving, if you need to re-visit the same page to verify data, **do not** try to navigate within the redirected page (redirect destination is uncertain, elements may not exist). Close the old tab and re-open a new tab from the original tab (stable state).

❌ Anti-pattern:

```python
# Try to navigate back from within the redirected page after saving
redirected_page = SomePage(new_page)
assert redirected_page.is_page_loaded()    # redirect destination uncertain → fails
redirected_page.click(breadcrumb)          # element may not exist
```

✅ Best practice:

```python
# Close old tab after saving
finally:
    new_page.close()

# Original tab is in stable state, re-enter from here
assert original_home.is_page_loaded()
new_page_2 = original_home.open_target_in_new_tab(name)
try:
    # navigate to editing page in new tab → verify data
finally:
    new_page_2.close()
```

---

## IV. Data Comparison Verification Pattern (Final Verification)

When there is no Toast or UI feedback, use "write marker → save → reopen → read and compare" as the final verification loop.

```python
# ── Write phase ──
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
edit_page.fill_description(timestamp)
write_test_data("marker_key", timestamp)          # persist to config file

# ... save operation ...

# ── Verification phase (reopen editing page) ──
saved = read_test_data().get("marker_key")
actual = edit_page.get_description_text()
allure.attach(saved, name="Expected timestamp", ...)     # record to report regardless of outcome
allure.attach(actual, name="Actual timestamp", ...)
assert actual == saved, (
    f"Data mismatch: expected='{saved}', actual='{actual}'"
)
```

**Key points:**
1. Marker data must be **written to config file** (shared across test cases, not in-memory variables)
2. Regardless of assertion outcome, use `allure.attach()` to write both expected and actual values to the report
3. Assertion failure message must include **comparison of both values** for easy debugging

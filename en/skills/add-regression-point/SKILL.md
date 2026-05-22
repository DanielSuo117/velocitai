---
name: add-regression-point
description: Incrementally add regression test points to an existing PageObject. Trigger: add test point, add regression point, add test point, increase coverage, extend page methods.
---

# Add Regression Point — Add New Regression Test Points

## Applicable Scenarios

Add one or more regression test points to an **existing PageObject**. Unlike `gen-page-test` (which creates an entire new page), this skill does **incremental extension** on an existing page.

## Input Parameters

| Parameter | Required | Description | Example |
|------|------|------|------|
| Target PageObject | Yes | Existing page class name | `<ExistingPage>` |
| Page URL | Yes | Real accessible page URL (authenticated state) | https://example.com/xxx |
| New test points | Yes | Interaction elements to cover | Click favorite, filter type |

---

## Execution Flow (4 Steps)

### Step 1: Access Real Page to Extract New Element Locators

Use agent-browser in authenticated state to access the target URL. For each new test point, select the locator using the six-level priority from [locator-replacer](../locator-replacer/SKILL.md). Browser tool selection follows [agent-behavior P0.4](../../rules/agent-behavior/agent-behavior.md): use agent-browser for DOM exploration/locator collection; fall back to Playwright MCP if agent-browser is not installed.

### Step 2: Update PageObject

Append to `pages/<page_name>_page.py`:

**2a. Add new locator constants** (insert after existing constants, before methods)

```python
    # ↓ New locators (from real page, <date>)
    <NEW_LOCATOR_1> = "<real locator>"    # P<0-5>: description
    <NEW_LOCATOR_2> = "<real locator>"    # P<0-5>: description
```

**2b. Add new business methods** (insert before `is_page_loaded()`)

```python
    def click_<new_method_1>(self):
        self.click(self.<NEW_LOCATOR_1>)

    def click_<new_method_2>(self):
        self.click(self.<NEW_LOCATOR_2>)

    def is_page_loaded(self) -> bool:    # keep as the last method
        return self.is_visible(self.PAGE_IDENTIFIER)
```

### Step 3: Append Calls in the Corresponding Role's Regression Test

Based on the target PageObject's role:
- Corresponding role page → `tests/teacher/test_<feature>.py` (if no main flow test yet, inherit `<Role>BaseTest` when creating)
- Corresponding role page → `tests/<role>/test_<role>_flow.py`
- Corresponding role → `tests/<role>/test_<role>_flow.py`

Append to the corresponding `@allure.story` method:

```python
    # ↓ New regression point
    <page_instance>.click_<new_method_1>()
    <page_instance>.click_<new_method_2>()
```

**⚠️ If the new test point's navigation target leaves the portal layout** (e.g. leaves the sidebar navigation sub-route, immersive page), you must apply [case-round-trip](../case-round-trip/SKILL.md): the PageObject must provide `click_back_to_<landing>`, and the test case must explicitly return to the start page and assert at the end; otherwise the reset fixture for subsequent test cases will time out.

### Step 4: Sync Update `docs/`

- Append new method rows in the pages-catalog sub-file for the corresponding role:
  - Corresponding role → [pages-catalog.md](../../../docs/pages-catalog.md)
- Append regression point rows + key locator constants in the regression-points sub-file for the corresponding role:
  - Corresponding role → [regression-points.md](../../../docs/regression-points.md)

---

## Checklist

General checks (naming/imports/is_page_loaded/allure) → coding-conventions.md "New Test Checklist"

- [ ] All new locators are from the real page DOM, annotated with P0~P5 level at end of line
- [ ] Corresponding role's `test_<role>_flow.py` has been updated with new method calls
- [ ] Corresponding role's `docs/pages-catalog-<role>.md` has been synced
- [ ] Corresponding role's `docs/regression-points-<role>.md` has been synced
- [ ] If navigation target leaves portal layout, `case-round-trip` has been applied

## Notes

- **Do not modify existing methods** — only do incremental additions
- **No need to update** `pages/__init__.py` (page class already exists)
- If new test points require page navigation (jumping to a sub-page), consider creating a new independent PageObject (using `gen-page-test`)
- Locators are extracted directly from the real page — do not use placeholders

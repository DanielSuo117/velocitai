---
name: gen-page-test
description: One-click generation of PageObject + matching tests. Trigger: new page, generate page, gen page, create page, add page object.
---

# Gen Page Test — One-Click PageObject + Test Generation

## Usage

```
User input: Generate a page object and tests for <PageName> (URL: https://...), test points: click A, fill B, view C
```

## Input Parameters

| Parameter | Required | Description | Example |
|------|------|------|------|
| Page name | Yes | Business name | Course Management Page |
| Page URL | Yes | Real accessible page URL (authenticated state) | https://example.com/xxx |
| Role | Yes | An existing role in the project (e.g. `<role>`) | Corresponding role |
| Class name | No (auto-derived) | PascalCase | `<Role><Page>Page` |
| Regression test points | Yes | Interaction elements to cover | Click create, search, delete |

**Class name derivation rules**:
- Non-role-specific: name → English translation → PascalCase + `Page` suffix (e.g. `<Feature>Page`)
- Role-specific: `<Role>` + English translation → PascalCase + `Page` suffix (e.g. `<Role><Feature>Page`)
- Role file name prefix: `<role>_` (e.g. `<role>_<feature>_page.py`)

For the list of existing class names in the project, see [docs/pages-catalog.md](../../../docs/pages-catalog.md).

---

## Execution Flow (6 Steps)

### Step 1: Access the Real Page to Get DOM

`browser_navigate` (prepend `/entry?token=xxx` if needed) → `browser_snapshot` → `browser_evaluate` to extract elements. Select stable locators using the six-level priority (P0 → P5) from [locator-replacer](../locator-replacer/SKILL.md).

### Step 2: Generate the PageObject File

Create `pages/<snake_name>_page.py`:

```python
# Page name: <PageName>
from pages.base_page import BasePage


class <ClassName>(BasePage):
    # Locators — from real page (<date>, URL: <page URL>)
    <LOCATOR_1> = "<real locator>"    # P<0-5>: description
    <LOCATOR_2> = "<real locator>"    # P<0-5>: description
    PAGE_IDENTIFIER = "<page identifier locator>"    # P<0-5>: description

    def click_<method_1>(self):
        self.click(self.<LOCATOR_1>)

    def click_<method_2>(self):
        self.click(self.<LOCATOR_2>)

    def is_page_loaded(self) -> bool:
        return self.is_visible(self.PAGE_IDENTIFIER)
```

### Step 3: Update `pages/__init__.py`

```python
from pages.<snake_name>_page import <ClassName>

# Append "<ClassName>" to the __all__ list
```

### Step 4: Append a Story to the Corresponding Role's Test File

Target file: the `Test<Role>Flow` class in the corresponding role's `tests/<role>/test_<role>_flow.py` (inheriting `<Role>BaseTest`).

Example for a role:

```python
@allure.story("<Page Name>")
def test_<snake_name>(self):
    page_obj = <ClassName>(self.<role>_page)
    self.<role>_page.goto("<page URL>")
    assert page_obj.is_page_loaded(), "<Page Name> failed to load"
    page_obj.click_<method_1>()
    ...
```

If the navigation target leaves the portal layout, apply round-trip closure (see case-round-trip):

```python
@allure.story("<Page Name>")
def test_<snake_name>(self):
    self.<role>_home.click_<navigation>()
    page_obj = <ClassName>(self.<role>_page)
    assert page_obj.is_page_loaded(), "<Page Name> failed to load"
    page_obj.click_<method_1>()
    page_obj.click_back_to_<landing>()
    assert self.<role>_home.is_page_loaded(), "Failed to return to start page"
```

### Step 5: Verify in Real Environment

```bash
pytest tests/<role>/test_<role>_flow.py --env=<pre|prod> -v -k "test_<snake_name>"
```

**⚠️ Confirm `--env` with the user before running** (see [agent-behavior.md](../../rules/agent-behavior/agent-behavior.md) P0.2).

On failure → use [locator-replacer](../locator-replacer/SKILL.md) to re-extract locators, or [test-runner](../test-runner/SKILL.md) to analyze failure type.

### Step 6: Sync Update `docs/`

- `docs/pages-catalog.md`: append new page class + method table
- `docs/regression-points.md`: append regression points table + key locator section

---

## Post-Generation Checklist

General checks (naming/imports/is_page_loaded/allure) → coding-conventions.md "New Test Checklist"

- [ ] All locators are from the real page DOM, annotated with P0~P5 level at end of line
- [ ] `pytest tests/<role>/test_<role>_flow.py --env=<pre|prod> -v -k "test_<name>"` passes
- [ ] Corresponding role's `docs/pages-catalog.md` has been updated
- [ ] Corresponding role's `docs/regression-points.md` has been updated
- [ ] If the navigation target leaves the portal layout, [case-round-trip](../case-round-trip/SKILL.md) has been applied

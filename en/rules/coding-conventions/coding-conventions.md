---
paths:
  - "pages/**"
  - "tests/**"
  - "conftest.py"
---

# Code and Test Conventions

Applies to: `pages/**` and `tests/**`. Write only real-browser end-to-end regression tests; do not write mock unit tests.

---

## Python Naming

- Classes PascalCase / methods & variables snake_case / constants & locators UPPER_SNAKE_CASE

Method naming prefix conventions:

| Interaction Type | Prefix | Example |
|----------|------|------|
| Click button/link/tab | `click_` | `click_submit()` |
| Fill input field | `fill_` | `fill_search(keyword)` |
| Select dropdown/filter | `select_` | `select_type()` |
| Get text | `get_xxx_text` | `get_title_text()` |
| Wait for element | `wait_for_` | `wait_for_loading_done()` |
| Page load verification | `is_page_loaded` | `is_page_loaded()` → **every page must have one** |

**Import order**: stdlib → third-party libs (`allure`, `playwright`) → project modules (`from pages.xxx import ...`)

---

## PageObject Conventions

- All page classes inherit `BasePage`; add `# Page name: <Name>` as the first line of the file
- Locators declared as **class-level constants** (at top of class), with level annotated at end of line `# P0`~`# P5` (strategy → [locator-replacer/SKILL.md](../../skills/locator-replacer/SKILL.md))
- Locators **must** be declared as class-level constants; **forbidden** to hardcode selector strings inside methods
- Common operations already wrapped by `BasePage` (`click` / `fill` / `is_visible` / `get_text` / `wait_for_element` / `get_element_count`) should be **used first** to avoid re-implementation
- Playwright APIs not covered by `BasePage` (`self.page.context.expect_page()`, `self.page.keyboard`, `self.page.wait_for_timeout()`, `self.page.locator().wait_for(state="hidden")`, `self.page.eval_on_selector()`, etc.) can be called directly via `self.page`
- No assertions in PageObjects (except `is_page_loaded`); `is_page_loaded` must be implemented, placed at end of class

❌ Anti-pattern: hardcoded selector inside a method

```python
def click_some_button(self):
    self.click("css=.some-button")              # selector scattered in method, cannot be maintained centrally
```

✅ Best practice: centralized locator management + prefer BasePage wrappers

```python
# Page name: <Page Name>
from pages.base_page import BasePage
class SomeFeaturePage(BasePage):
    FEATURE_TITLE = "css=span.feature-title"  # P3
    LEFT_MENU = "css=ul.menu-box"             # P3
    LOADING = "css=.loading-state"            # P3

    def get_title(self) -> str:
        return self.get_text(self.FEATURE_TITLE)           # BasePage already wraps this, use it

    def wait_for_loading_done(self, timeout=30000):
        self.page.locator(self.LOADING).wait_for(         # BasePage doesn't wrap state="hidden",
            state="hidden", timeout=timeout,              # can use self.page directly
        )

    def is_page_loaded(self) -> bool:
        return self.is_visible(self.FEATURE_TITLE) and self.is_visible(self.LEFT_MENU)
```

---

## Test File Organization

- Add `# File purpose: <brief description>` as the first line; each file corresponds to one `Test<Role><Feature>` class
- Split by role into directories: `tests/<roleA>/`, `tests/<roleB>/`
- Base class path: each role has `tests/<role>/<role>_base_test.py::<Role>BaseTest`; common root base class `tests/base_test.py::BaseTest`

### Test Method Add and Modify Order

- **Adding**: append to end of class; forbidden to insert between existing methods
- **Modifying**: modify in-place; forbidden to reorder methods

```python
class Test<Role>Flow(BaseTest):
    def test_case_a(self): ...   # existing — modify in-place
    def test_case_b(self): ...   # existing — keep order
    def test_case_c(self): ...   # new — append to end
```

---

## Base Class Conventions (Mandatory)

### Role Base Class: Inherit `<Role>BaseTest`

Class-level shared `self.<role>_page` (already logged in); subclasses navigate to target pages via additional class-scope fixtures. **Forbidden** to repeat token login or manually override `_login_setup` in test cases.

```python
@allure.feature("<Role> Main Flow")
class Test<Role>Flow(<Role>BaseTest):
    @allure.story("Login → Home")
    def test_xxx(self):
        home = SomeHomePage(self.<role>_page)
        assert home.is_page_loaded(), "Home page failed to load"
```

Shared logic across test cases should be added to the base class or a derived sub-base class; do not copy it into each test case.

**Forbidden** to navigate back to another role's domain within a role's class (see [browser-context.md](../playwright/browser-context.md)).

---

## Test Case Writing Conventions

- Allure decorators: class-level `@allure.feature("module name")`, method-level `@allure.story("feature point")`
- Assertion failure messages must be in English; after each navigation `assert page_obj.is_page_loaded(), "... failed to load"`
- Cross-tab scenarios: PageObject method returns a new `Page`; test case instantiates the corresponding PageObject from it
- Forbidden `time.sleep()` (blocks Python process, Playwright cannot execute any operations during this time); use `page.wait_for_timeout()` for async render waits after SPA menu/tab switching (Playwright internal wait, browser event loop still running); see [timeout-and-wait.md](../playwright/timeout-and-wait.md)

---

## Isomorphic Element Data-Driven Pattern

When ≥3 UI elements with the same structure (Tabs / menu items / cards) need to be verified one by one, use **data-driven loop + `allure.step`** instead of N independent test methods:

```python
@allure.story("Coverage description")
def test_all_xxx(self):
    items = [("Element A", "is_a_loaded", "A failed to load"), ("Element B", "is_b_loaded", "B failed to load")]
    for name, check_method, fail_msg in items:
        with allure.step(f"Click [{name}] and verify"):
            assert getattr(page_obj, check_method)(), fail_msg
```

Use independent test methods when verification logic differs significantly.

---

## New Test Checklist

1. Inherits the role's corresponding `<Role>BaseTest`, no repeated login
2. All PageObjects have `is_page_loaded()` and it is asserted in test cases
3. `pages/__init__.py` exports the new PageObject
4. Class has `@allure.feature`, method has `@allure.story`; assertion messages in English
5. Did not navigate back to another role's domain
6. Passed in real environment: `pytest tests/<path>.py --env=<pre|prod> -v -k <case>`
7. Corresponding role's `docs/pages-catalog.md` / `docs/regression-points.md` has been synced

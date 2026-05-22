---
name: architecture
description: POM layering and context sharing decision tree. Trigger: architecture, layering, POM, Page Object, base class design, add new role.
---

# Architecture Decisions — POM Layering and Context Sharing Patterns

## Applicable Scenarios

- Deciding whether to introduce a new base class when adding a new role/endpoint
- Deciding whether a set of test cases should share a page / context
- Explaining POM layering to new team members

---

## General POM Layer Skeleton

```
┌─────────────────────────────────────────────┐
│                  tests/ Test Layer            │
│  Split by role: test_<role>_flow.py          │
│  Each test class inherits Base (or Role-Base) │
├─────────────────────────────────────────────┤
│                  pages/ Page Object Layer     │
│  Base ← Login ← Landing ← Detail / ...       │
│  Generic role prefix: Role<Role><Page>Page   │
├─────────────────────────────────────────────┤
│                  config/ Config Layer         │
│  URL, Token, browser params switch by env    │
├─────────────────────────────────────────────┤
│                  conftest.py Fixture Layer    │
│  browser → context → page → Role-specific base │
└─────────────────────────────────────────────┘
```

**Data flow**: `config` → `conftest` (read config, create fixtures) → `pages` (receive page object) → `tests` (compose page objects and execute assertions)

---

## PageObject Skeleton

```python
# Page name: <Page Name>
from pages.base_page import BasePage


class <PageName>(BasePage):
    # Locator constants (at top of class)
    <LOCATOR_CONSTANT> = "<selector>"   # P<0-5>: description
    PAGE_IDENTIFIER = "<selector>"      # Page load anchor

    # Business methods (prefix: click_ / fill_ / select_ / get_xxx_text / wait_for_ / is_xxx_visible)
    def click_<action>(self):
        self.click(self.<LOCATOR_CONSTANT>)

    # Page load verification (must implement, place last)
    def is_page_loaded(self) -> bool:
        return self.is_visible(self.PAGE_IDENTIFIER)
```

---

## Context Sharing Pattern Decision Tree

```
Does a set of test cases satisfy all 3 conditions?
   1. Same domain (no cross-endpoint)
   2. Has unified precondition (login, role switch...)
   3. Has unified starting page (can be reset)
       │
       ├─ Yes (all 3 satisfied)
       │    └→ Class-level shared context
       │       - Use scope="class" page fixture (implementation in browser-config skill)
       │       - Dedicated base class: class setup completes precondition; function-scope autouse resets start page
       │       - Test cases must be round-trip closed (see case-round-trip skill)
       │
       └─ No (any condition not met)
            └→ Function-level independent context
               - Each test case has independent browser.new_context() + new_page()
               - Each test case logs in independently
```

**Notes:**

- ❌ Session-level cross-class shared context is forbidden (unclear responsibility boundary across classes)
- ❌ Cross-domain within the same class is forbidden (will contaminate the shared context)
- Detailed rules → [rules/playwright/browser-context.md](../../rules/playwright/browser-context.md) "Browser Context" section

---

## Intra-Class Page Relay Pattern

**Scenario**: Multiple test cases in the same class form a **linear flow chain**, where the next test case starts where the previous one ended, without needing to log in from scratch.

```
test_a (search course)
    ↓ page stays on search results
test_b (click course → new tab opens course home)
    ↓ new tab saved as class attribute
test_c (continue operating on course home)
    ↓ use page from class attribute directly
```

### Implementation Key Points

1. **class-scope fixture completes one-time login**: override parent `_login_setup` to no-op, share via `class_page` + `request.cls.page`
2. **Page relay between test cases**: when a test opens a new tab, save the new page to a class attribute (`type(self).<attr> = new_page`); subsequent tests access via `self.<attr>`
3. **New tab stays open**: pages in the relay chain remain open until the class ends and context is automatically destroyed
4. **Test order equals flow order**: pytest executes methods in the order they appear in the file by default

### Skeleton

> For the implementation of the `class_page` fixture, see [browser-config](../browser-config/SKILL.md) "Fixture Layer Template".

```python
class TestSomeFlow(BaseTest):

    @pytest.fixture(autouse=True)
    def _login_setup(self):
        yield  # no-op, overrides parent

    @pytest.fixture(scope="class", autouse=True)
    def _shared_setup(self, class_page, token, request):
        login_page = LoginPage(class_page)
        login_page.login_with_token(BASE_URL, token)
        request.cls.page = class_page

    def test_step_1(self):
        ...  # self.page already injected by _shared_setup, class-level shared

    def test_step_2(self):
        new_page = some_page.click_open_new_tab()
        type(self).detail_page = new_page  # save to class attribute for later tests

    def test_step_3(self):
        detail = SomeDetailPage(self.detail_page)  # direct relay
        ...
```

### Applicability Conditions

- ✅ Within the same class, test cases have clear sequential dependencies
- ✅ New tab is still on the same domain or carries authentication (no second login needed)
- ❌ If test cases have no dependencies, do not use the relay pattern (use independent function-scope pages instead)

---

## Steps to Add a New Role

1. Decision: use the decision tree above to determine if the new role's test cases can share context
2. PageObject: name as `Role<Role><Page>Page`, file name prefix `role_<page>`, inherit `BasePage`
3. Base class (if using class-level sharing): create `tests/<role>/<role>_base_test.py::<Role>BaseTest` inheriting `BaseTest`, implement login + switch + start page assertion
4. Test cases: `tests/<role>/test_<role>_flow.py::Test<Role>Flow` inherits the new base class
5. Docs: append a row in [docs/architecture.md](../../../docs/architecture.md)
6. Directory: add new page export to `pages/__init__.py`

---

## Decision Implementation Reference

For the current project's implementation (specific class names, fixtures, start pages) → [docs/architecture.md](../../../docs/architecture.md).

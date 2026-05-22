---
name: locator-replacer
description: Replace placeholder locators with real selectors (six-level priority). Trigger: replace locator, locator, selector, locator failed, element not found, DOM analysis.
---

# Locator Replacer — Locator Replacement Skill

## Applicable Scenarios

- Replace `text=` placeholder locators in page objects with real selectors
- After a frontend build, existing selectors break and need to be re-located
- Choosing the best locator strategy for new page elements

---

## Locator Selection Strategy (Six-Level Priority)

Try levels from highest to lowest, **stop at the first match**. Prefer semantic information already present on the page; avoid attributes that require extra work from the frontend:

### P0: User-Visible Semantic Elements (Role + Text)

```python
# Locate via ARIA role + visible text
LOGIN_BTN = "role=button[name='Login']"
NAV_LINK = "role=link[name='<feature name>']"
SEARCH_INPUT = "role=textbox[name='Search']"
```

- Based on accessibility semantics — consistent with what the user sees
- CSS-refactor resistant: role does not depend on class/id
- Build-tool resistant: unaffected by Webpack/Vite hash class names
- **Must be updated when UI copy changes**

### P1: Visible Text Locator

```python
# Exact match
FEATURE_BTN = "text=<feature name>"
# Contains match (text may be nested in child elements)
FEATURE_TAB = "text=<feature name>"
```

- Simple and direct, no extra attributes needed
- Suitable when copy is stable and the element is unique
- **Note:** `text=` is the placeholder approach for this project. If analysis confirms `text=` is already stable and unique, it can be kept and marked `# P1: text (verified unique)`

### P2: Form-Specific Attributes

```python
# placeholder locator
EMAIL_INPUT = "[placeholder='Enter email']"
# label association
PASSWORD_INPUT = "css=input[name='password']"
# type attribute
SUBMIT_BTN = "css=button[type='submit']"
```

- Only applicable to form elements (input/select/textarea/button)
- `name` attribute is usually backend-defined and relatively stable
- `placeholder` follows copy changes — medium stability

### P3: Stable CSS Class / ID

```python
# Business semantic class name — stable
COURSE_CARD = "css=.list-card"
LOGIN_FORM = "css=#login-form"
NAV_MENU = "css=.main-navigation"

# ⚠️ The following are hash class names — absolutely forbidden
# BAD: "css=.sc-bdVaJa.bVjGWg"         (styled-components hash)
# BAD: "css=.css-1a2b3c"                (CSS Modules hash)
# BAD: "css=[class*='_component_']"     (Vite CSS Modules)
```

**Hash class name identification rules (must skip):**

| Build Tool | Hash Class Characteristics | Example |
|----------|-------------|------|
| styled-components | Random letter combination | `.sc-bdVaJa`, `.bVjGWg` |
| CSS Modules | Underscore + hash | `.header_abc123`, `._component_1x2y3` |
| Vite | Short hash suffix | `.module_1a2b3c` |
| Tailwind JIT | Dynamic utility classes | `.[\31 /2]`, `.[color:red]` |
| Emotion | css- prefix | `.css-1a2b3c` |

**Usable class name characteristics:**
- Contains business semantics: `.list-card`, `.login-form`, `.nav-menu`
- Follows BEM naming: `.header__title`, `.card--active`
- Has clear prefix: `.app-feature-list`, `.app-header`

### P4: `data-testid` Dedicated Test Attribute

```python
# Playwright locator syntax
SUBMIT_BTN = "[data-testid='submit-button']"
```

- Unaffected by style refactoring, copy changes, or build tools
- **Requires frontend developer collaboration to add** — cannot be done independently
- Suitable for complex elements where P0~P3 cannot provide stable locators
- Use if the page already has `data-testid`, but don't require the frontend to add it for every element

### P5: Relative XPath / CSS Structure Locator (Last Resort)

```python
# ✅ Relative path — starting from a stable ancestor node
SUBMIT_BTN = "xpath=//div[@class='login-form']//button[@type='submit']"
FIRST_COURSE = "css=.course-list > .course-item:first-child"

# ❌ Absolute path — absolutely forbidden
# BAD: "xpath=/html/body/div[1]/div[2]/ul/li[3]/button"
```

**XPath writing rules:**
- Start from the nearest stable ancestor node to the target element
- Anchor the ancestor node with business semantic attributes (class/id/data-*)
- Path depth must not exceed 3 levels
- Absolute paths (starting from `/html/body`) are forbidden
- Pure numeric index locators (`div[3]`) are forbidden, unless it's a list and you genuinely need the Nth item

---

## Execution Flow

### Step 1: Analyze Target Page DOM

Use agent-browser to open the target page and get interactive element information (tool selection follows [agent-behavior P0.4](../../rules/agent-behavior/agent-behavior.md); fall back to Playwright MCP if agent-browser is not installed):

```
Steps:
1. browser_navigate → access target page (authenticated state)
2. browser_snapshot → get page accessibility tree
3. browser_evaluate → run JS to extract element attributes:
   - document.querySelectorAll('[data-testid]')  → existing testids
   - document.querySelectorAll('[role]')          → ARIA roles
   - document.querySelectorAll('button, a, input') → interactive elements
```

### Step 2: Choose Locator Strategy for Each Element

For each placeholder locator in the page object, try P0→P5 in order, stop when a match is found:

| Check Order | Condition | Use |
|---------|------|------|
| P0 | Has role + name | `role=button[name='...']` |
| P1 | text= is unique and stable | `text=...` (mark "verified unique") |
| P2 | Form attributes (placeholder/name/type) | `[placeholder='...']` |
| P3 | Stable CSS class (non-hash) | `css=.xxx` |
| P4 | Has data-testid | `[data-testid='...']` |
| P5 | None of the above | Relative XPath (≤3 levels) |

### Step 3: Update the Page Object

```python
class <PageName>(BasePage):
    # Locators — replaced with real selectors (<date>)
    <PRIMARY_ACTION_BTN> = "role=button[name='<button text>']"  # P0: ARIA role
    <SECONDARY_LINK> = "text=<link text>"                        # P1: text (verified unique)
    PAGE_IDENTIFIER = "role=heading[name='<page title>']"        # P0: ARIA role
```

**Update rules:**
- Annotate the locator level at the end of each locator line (`# P0: ARIA role` / `# P1: text` / ... / `# P4: testid` / `# P5: XPath`)
- If `text=` is verified stable and unique, mark comment as `# P1: text (verified unique)`
- Remove the original `# Locators — to be replaced with real selectors` comment
- Update to `# Locators — replaced with real selectors (date)`

### Step 4: Verify

```bash
# Run the specified test case in the corresponding role's regression file (confirm --env with user before running, see agent-behavior P0.2)
pytest tests/<role>/test_<role>_flow.py --env=<pre|prod> -v -k "test_<story_name>"
```

### Step 5: Sync Update Docs

Update the "Key Locators" section for the corresponding PageObject in [docs/regression-points.md](../../../docs/regression-points.md).

---

## Locator Quality Checklist

After replacement, verify each item:

- [ ] No absolute XPath (`/html/body/...`)
- [ ] No hash class names (`sc-xxx`, `css-xxx`, `_module_xxx`)
- [ ] No pure numeric index (`div[3]`, unless getting the Nth item in a list)
- [ ] Each locator has level annotated at end of line (`# P0` ~ `# P5`)
- [ ] XPath depth does not exceed 3 levels
- [ ] Main-flow tests pass in the real environment

---

## Common Issue Handling

### Same text appears multiple times making `text=` non-unique

Fall back to P3/P5, use parent container + text combination: `css=.list-card:first-child >> text=View Details`

### Element has no stable attributes at all

Request that the frontend team add `data-testid` (P4) with a list of elements; temporarily use P5 relative XPath as a bridge.

### Frontend build makes selectors break in bulk

Check if hash class names were used (violates P3) → prioritize upgrading to P0/P1 (unaffected by builds) → if copy changed, update to match new copy.

---
name: page-load-assertion
description: Four verification modes and call hierarchy for is_page_loaded(). Trigger: page assertion, is_page_loaded, page loaded, page load verification.
---

# Page Load Assertion — Page Load Assertion Methodology

## Core Idea

Determining that a page is "working correctly" is not checking the HTTP status code — it's verifying that **the key elements the user can see are actually rendered**. This is implemented uniformly via each PageObject's `is_page_loaded()` method.

---

## Four Verification Modes for `is_page_loaded()`

From least to most strict:

### Mode A: Single-Element Verification (Simplest)

Check if the page's **unique signature container** is visible. Suitable for pages with simple structure where one element is sufficient to distinguish:

```python
PAGE_CONTAINER = "css=.feature-container"    # P3

def is_page_loaded(self) -> bool:
    return self.is_visible(self.PAGE_CONTAINER)
```

### Mode B: Dual-Element AND Combination (Recommended Default)

**Container + content** double verification, ensuring "page skeleton present + data rendered":

```python
PAGE_CONTAINER = "css=.feature-container"    # P3
PAGE_TITLE = "text=Welcome"                   # P1

def is_page_loaded(self) -> bool:
    return self.is_visible(self.PAGE_CONTAINER) and self.is_visible(self.PAGE_TITLE)
```

### Mode C: Multi-Element + Active State Verification (Strictest)

On top of structure and content, also verifies the **current UI state** (e.g. a tab is in active state). Suitable for pages that serve as the "start state determination" semantic:

```python
PAGE_TITLE = "css=span.page-title"                                    # P3
TAB_BAR = "css=ul.tab-bar"                                            # P3
DEFAULT_TAB_ACTIVE = "css=ul.tab-bar li.tab.active >> text=DefaultTab" # P3+P1

def is_page_loaded(self) -> bool:
    return (
        self.is_visible(self.PAGE_TITLE)
        and self.is_visible(self.TAB_BAR)
        and self.is_visible(self.DEFAULT_TAB_ACTIVE)
    )
```

Note: State-class selectors (`.active` / `aria-selected` etc.) **must be anchored with text**, otherwise `.active` will drift to the newly activated object after tab switching.

### Mode D: Delegate to Semantic Method

Extract the verification logic into a business-meaningful method name, making it easier to call independently in setup fixtures:

```python
def is_page_loaded(self) -> bool:
    return self.is_login_success()

def is_login_success(self) -> bool:
    return self.is_visible(self.SUCCESS_FLAG) and self.is_visible(self.NAV_LIST)
```

---

## Mode Selection Decision Tree

```
New page needs is_page_loaded()
│
├─ Page structure is simple, one unique container is sufficient?
│  └─ Yes → Mode A (single element)
│
├─ Need to confirm content is also rendered?
│  └─ Yes → Mode B (container + content, recommended default)
│
├─ This page is the reset fixture's start point, need to check UI state?
│  └─ Yes → Mode C (multi-element + active state)
│
├─ Verification logic also needs to be called independently in setup?
│  └─ Yes → Mode D (delegate to semantic method)
│
└─ Container may exist but content not rendered (SPA sub-tab switch / async load)?
   └─ Yes → Mode E (JS evaluate to check child element count)
```

---

## Principles for Choosing Verification Elements

| Principle | Description |
|------|------|
| Choose elements unique to this page | Don't use common header/footer; choose containers or text only present on this page |
| Prefer structural containers | e.g. `.feature-container`, `.detail-wrapper`; page skeleton is less likely to change |
| Text elements anchor business semantics | e.g. `text=Welcome`, confirms content is rendered |
| State-class selectors need text anchor | `.active` drifts with operations, must add `>> text=specific text` to lock it |
| Don't use dynamic data | Specific numbers, usernames, etc. cause unstable assertions due to data changes |

### Three-Level Stability of Assertion Targets

Core principle: prefer **template-level** text (fixed page frame titles); forbid **data-level** content (dynamic counts, dates). In multi-view scenarios, each assertion target must simultaneously satisfy "template-level + view-unique".

Full rules with anti-patterns/best practices → [assertion-patterns.md](../../rules/playwright/assertion-patterns.md) "Assertion Target Stability" section.

### Mode E: Blank Screen Detection + Three-State Judgment (Empty vs. Has Data)

In SPA applications, the container div may exist in the DOM and `is_visible` returns true, but internal components have not mounted (blank screen). In this case Mode A/B's `is_visible(container)` will incorrectly judge as normal.

**The content area can have three states, each must be handled separately:**

```
Content area state
│
├─ Blank screen (render failed)
│  Content area child element count = 0, component not mounted
│  → Judgment: ❌ Test fails, report "Content area not rendered, possible blank screen"
│
├─ Empty data (no business data but rendering is normal)
│  Content area child count > 0, but no business data items
│  Usually has empty state prompt (image + "No data" / "No favorites yet" etc.)
│  → Judgment: ✅ Rendering normal, page genuinely has no business data
│
└─ Has data (normal rendering)
   Content area child count > 0, with business data items
   → Judgment: ✅ Rendering normal
```

**Implementation template:**

```python
# Locators
CONTENT_CONTAINER = "css=<main content container>"         # page skeleton container
EMPTY_STATE = "css=<empty state element>"                   # empty state component (image+text)
DATA_ITEM = "css=<business data item>"                      # single data entry

def get_content_render_state(self) -> str:
    """Returns content area render state: 'blank' / 'empty' / 'loaded'."""
    return self.page.evaluate("""() => {
        const container = document.querySelector('<content container selector>');
        if (!container) return 'blank';
        const contentArea = container.querySelector('<content area selector>');
        if (!contentArea || contentArea.children.length === 0) return 'blank';
        return 'loaded';
    }""")

def is_content_rendered(self) -> bool:
    """Blank screen detection: container exists but content area has no children → False.
    Both empty data and has data count as successfully rendered → True."""
    return self.get_content_render_state() != 'blank'

def has_data_items(self) -> bool:
    """Whether there are business data items (excluding empty state)."""
    return self.get_element_count(self.DATA_ITEM) > 0
```

**Three-state assertions in test cases:**

```python
# Layer 1: render check (blank screen vs. rendered)
is_rendered = page_obj.is_content_rendered()
if not is_rendered:
    assert False, "Content area not rendered, possible blank screen"

# Layer 2 (optional): empty data vs. has data
# Decide based on business expectation whether further distinction is needed
if page_obj.has_data_items():
    # Has data → can further verify data content
    pass
else:
    # Empty data → record in report, don't treat as failure
    allure.attach("This tab currently has no business data (empty state)", ...)
```

**⚠️ Pitfalls:**

| Wrong Approach | Problem | Correct Approach |
|---------|------|---------|
| `innerText.length > N` to detect blank screen | Empty state hint text may be short, misidentified as blank screen | `children.length > 0` |
| Treating empty data as failure | No favorites/wrong answers is a valid business state | Only fail on blank screen, just record empty data |
| Only checking container `is_visible` | Container div may exist but child components not mounted | JS evaluate to check child elements |

**Applicable scenarios:**
- Switching multiple sub-tabs within the same container, some tabs may have no business data
- Async-loaded components may not render due to interface timeout
- SPA routes where page skeleton renders first and content loads later

---

## Call Hierarchy

1. **class setup**: after login `assert home.is_page_loaded(), "Home page failed to load"`
2. **function reset**: `if not self.home.is_page_loaded(): click_nav_home(); assert ...`
3. **test body**: after each navigation `assert target.is_page_loaded(), "<Page> failed to load"`

---

## Rule Constraints

1. **Every PageObject must implement `is_page_loaded()`** — returns `bool`, placed as the last method in the class
2. `is_page_loaded()` internally only uses `is_visible()` combinations, **does not throw exceptions**

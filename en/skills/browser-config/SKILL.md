---
name: browser-config
description: Browser viewport / headless / timeout layered configuration. Trigger: viewport, browser config, navigation timeout, headless, slow_mo, incognito.
---

# Browser Launch Configuration — viewport / incognito / timeout separation

## Core Principle

**All browser configuration is declared centrally in the config file, injected via fixture layers, and must not be hardcoded in test cases or PageObjects.**

---

## I. Complete pytest Browser Configuration Architecture

### Configuration Layers

```
Config file (constant declarations)
  │
  ├─ browser fixture (session-level)
  │    └─ headless / slow_mo / incognito
  │
  ├─ page fixture (function-level)
  │    └─ viewport / timeout / navigation_timeout
  │
  └─ class_page fixture (class-level)
       └─ viewport / timeout / navigation_timeout
```

### Config File: All Constants Declared Centrally

```python
# Browser configuration
HEADLESS = False              # True: headless mode (CI); False: headed mode (local debug)
SLOW_MO = 500                 # Delay between each step (ms), for visual observation; set to 0 for CI
DEFAULT_TIMEOUT = 15000       # Element operation timeout (ms)
DEFAULT_NAVIGATION_TIMEOUT = 15000  # Page navigation timeout (ms)
VIEWPORT_WIDTH = 1280         # Viewport width
VIEWPORT_HEIGHT = 900         # Viewport height
```

### Fixture Layer Template

```python
@pytest.fixture(scope="session")
def browser(playwright_instance):
    browser = playwright_instance.chromium.launch(
        headless=HEADLESS, slow_mo=SLOW_MO, args=["--incognito"],
    )
    yield browser
    browser.close()

@pytest.fixture                   # function-level: independent context + page per test case
def page(browser):
    context = browser.new_context(viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
    page = context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT)
    page.set_default_navigation_timeout(DEFAULT_NAVIGATION_TIMEOUT)
    yield page
    page.close(); context.close()

@pytest.fixture(scope="class")    # class-level: shared context + page within the same class
def class_page(browser):
    # same as page fixture, scope="class"
    ...
```

**Key constraint**: `viewport` at context layer, `timeout` at page layer, `--incognito` at browser layer — the three must not be mixed across layers.

---

## II. Viewport Size Selection

### Core Constraint: Viewport Height Must Fit Physical Screen

Viewport height must not exceed the physical screen's available height (screen resolution − browser toolbar − system taskbar), otherwise the browser window bottom will extend beyond the screen, obscuring page content at the bottom and making it uninteractable.

### Correct Strategy: Keep Width, Moderately Increase Height (Without Exceeding Screen)

Scaling up viewport proportionally for responsive pages has no effect (visible ratio unchanged); keep width, moderately increase height (without exceeding screen).

| Option | Viewport | Effect |
|------|----------|------|
| Default | 1280x720 | Baseline, relatively small |
| **Recommended** | **1280x900** | **Fits MacBook screen, window doesn't exceed screen** |
| External monitor | 1280x1080 | Fits Full HD display |
| Too large (wrong) | 1280x1440 | Exceeds most screens, bottom obscured |
| Proportional scale (wrong) | 2560x1440 | No improvement for responsive pages' visible ratio |

---

## III. Incognito Mode

Enable for pytest test browser (isolated environment), optional for MCP debug browser (may need to retain login state). Passed to the browser layer via `launch(args=["--incognito"])`.

---

## IV. Navigation Timeout and Element Timeout Separation

Both default to 15s. The reason for separation: when page resources are heavy, you can **increase navigation timeout independently** without affecting element operation's fast feedback.

```python
page.set_default_timeout(DEFAULT_TIMEOUT)                    # element operations
page.set_default_navigation_timeout(DEFAULT_NAVIGATION_TIMEOUT)  # page navigation
```

---

## Checklist

- [ ] `viewport` passed in at `new_context()` (context layer), not in browser layer
- [ ] Both `set_default_timeout` and `set_default_navigation_timeout` are set (kept separate)
- [ ] `--incognito` enabled on pytest test browser; optional for MCP debug browser
- [ ] No hardcoded browser configuration values in test cases or PageObjects

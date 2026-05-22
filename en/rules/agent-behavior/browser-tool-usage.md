---
# Not auto-loaded. Referenced on-demand by agent-behavior.md P0.4.
---

# Browser Tool Usage Rules (P0.4 Series Detailed Anti-Patterns/Best Practices)

> General tool selection rules → [agent-behavior.md](./agent-behavior.md) P0.4

---

## P0.4.1 · agent-browser click Failure: Immediately Fall Back to eval

**Trigger**: `agent-browser click @ref` has no effect once (no navigation / no UI change).

**Reason**: `agent-browser click` is based on the CDP accessibility tree. For non-semantic `<div>` / `<span>` + frontend framework event binding (Vue `@click`, React `onClick`), CDP clicks sometimes cannot trigger synthetic events.

**Rule**: One no-response → immediately fall back to JS click; forbidden to retry repeatedly.

✅ Best practice:

```bash
agent-browser click @e27   # no response
# immediately fall back to JS click
agent-browser eval "(function(){ document.querySelectorAll('.target-selector')[0].click(); })()"
```

---

## P0.4.2 · After agent-browser Triggers a New Tab, Must Switch Manually

**Trigger**: `agent-browser click` or `eval` triggered a new tab.

**Rule**: agent-browser does not automatically switch to the new tab. After the operation, must list → switch → snapshot.

✅ Best practice:

```bash
agent-browser click @e11
agent-browser tab list            # confirm new tab
agent-browser tab t2              # switch
agent-browser snapshot -i -c      # new page content
```

---

## P0.4.2.1 · Playwright MCP Cross-Subdomain SSO Login-Free: Must Wait for networkidle Before Navigating

**Trigger**: Using Playwright MCP to debug a subdomain page that requires SSO authentication.

**Reason**: `browser_navigate` does not wait for `networkidle`; after token login, the SSO cookie may still be asynchronously written; navigating to the subdomain directly may have the cookie not yet ready → redirected to login page.

**Rule**: After token login-free access, must use `browser_wait_for` to confirm the login success indicator appears before navigating to the subdomain.

✅ Best practice:

```
browser_navigate → <BASE_URL>/entry?token=JWT
browser_wait_for → text="<login success indicator>"      # confirm login complete
browser_navigate → <TARGET_SUBDOMAIN>/...
browser_wait_for → text="<target page signature text>"   # confirm subdomain page loaded
```

**Fallback when still failing**: Use an independent Python script with explicit `wait_for_load_state("networkidle")`:

```python
page.goto(f"{BASE_URL}/entry?token={TOKEN}")
page.wait_for_load_state("networkidle")
page.goto(TARGET_URL)
page.wait_for_load_state("networkidle")
```

---

## P0.4.3 · Must Verify Existing Locators Before Writing New Test Cases

**Trigger**: Adding new test cases or extending methods for an existing PageObject.

**Reason**: Pages get updated iteratively; existing locators may have expired.

**Rule**: Use `agent-browser` to open the real page and verify the existing locators for the target area. When a mismatch is found: fix the locator → sync update `docs/regression-points.md` → check other test case references.

✅ Best practice:

```bash
agent-browser open <page URL>
agent-browser snapshot -s "<target container selector>"
# Confirm actual text matches locator in code; if not, fix first before writing test cases
```

---

## P0.4.4 · Bulk Multi-View Collection Uses eval Loop, Not Manual One-by-One Interaction

**Trigger**: Need to collect multiple tabs / menu items / panel content (N ≥ 3).

**Rule**: Use JS eval loop for bulk collection; forbidden to click + snapshot one by one (N elements = 2N commands).

✅ Best practice:

```bash
for idx in 0 1 2 3 4 5 6 7 8 9 10 11 12 13; do
  agent-browser eval "(function(){
    var items = document.querySelectorAll('ul.nav-list li');
    items[$idx].click();
    return items[$idx].innerText.trim();
  })()"
  sleep 3
  agent-browser eval "(function(){
    return document.querySelector('main').innerText.substring(0, 300);
  })()"
done
```

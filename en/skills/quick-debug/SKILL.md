---
name: quick-debug
description: On test failure, jump directly to the problem page via token login and debug in-place. Trigger: debug, troubleshoot, locator failure, timeout, element not found, assertion failure.
---

# Quick Debug — Rapid Triage and Fix

## Core Idea

**Skip the full flow from login to the problem node; go directly to the target page via token login-free access and debug in-place.**

Leverage the project's existing token URL login-free mechanism, combined with browser tools, to perform DOM exploration, locator verification, and wait strategy adjustment directly on the problem page. Fix and verify in-place without re-running the full test flow.

---

## Main Flow (5 Steps)

```
Step 1: Parse failure information
    ↓
Step 2: Construct login-free redirect URL
    ↓
Step 3: Redirect to target page without login
    ↓
Step 4: Diagnose the problem (decision tree)
    ↓
Step 5: Fix + in-place verification
```

### Step 1: Parse Failure Information

Extract from the stack trace / user description: failed test name, error type (TimeoutError / AssertionError), failed locator, URL at time of failure. If information is insufficient, read the test code to infer.

### Step 2: Construct Login-Free Redirect URL

Read the token for the corresponding environment from the config file.

**⚠️ Must confirm `--env` with the user before login-free access** (see [agent-behavior P0.2](../../rules/agent-behavior/agent-behavior.md)).

**Two cases:**

| Case | Strategy |
|------|------|
| Target page has a clear URL path | Login-free first (`/entry?token=<JWT>`), then navigate to target path |
| Target page requires interaction to reach (dialog, new tab, etc.) | Login-free to the nearest directly-accessible parent page, then perform minimum navigation to reach the target |

### Step 3: Redirect to Target Page Without Login

`browser_navigate → <base_url>/entry?token=<JWT>` → navigate to target path → verify `is_page_loaded()`. If login-free fails (redirected back to login page) → prompt user to refresh token.

### Step 4: Diagnose the Problem

See the "Diagnosis Decision Tree" section below.

### Step 5: Fix + In-Place Verification

**Call the corresponding skill based on diagnosis result:**

| Diagnosis Result | Call Skill |
|---------|-----------|
| Locator issue | [locator-replacer](../locator-replacer/SKILL.md) |
| Wait strategy issue | [wait-strategy](../wait-strategy/SKILL.md) |
| Page load assertion issue | [page-load-assertion](../page-load-assertion/SKILL.md) |
| Major page redesign | Report to user, suggest [gen-page-test](../gen-page-test/SKILL.md) to regenerate |
| Assertion expected value changed | Report the difference, let user decide whether to update expected values |

**In-place verification:** After fixing, directly verify on the current browser page (re-execute the failed operation with Playwright MCP). Once confirmed, suggest that the user re-run the full tests.

---

## Diagnosis Decision Tree (Step 4 Expanded)

First use agent-browser to quickly scan the current page DOM (fall back to Playwright MCP if not installed), then follow the corresponding branch based on error type:

```
Error type classification
    ├── A. Locator issue (element not found / matches multiple)
    ├── B. Timeout issue (element exists but loads slowly / network latency)
    ├── C. Assertion issue (element exists but content/state doesn't match expectation)
    └── D. Page structure change (overall page redesign / route change)
```

### Branch A: Locator Issue

**Criteria:** `locator.count() == 0` or `strict mode violation` (multiple matches)

**Investigation steps:**
1. Use agent-browser to capture a DOM snapshot of the problem area
2. Compare PageObject locator with actual DOM, determine cause: class name change / text change / dynamic rendering not complete

**Fix path** → call `locator-replacer` skill

### Branch B: Timeout Issue

**Criteria:** `TimeoutError` and element can appear after a longer wait, or `networkidle` not reached

**Investigation steps:**
1. Check if current page URL is correct (rule out navigation deviation); check if target element exists but is not visible (hidden / covered)
2. Determine cause: implicit wait insufficient / SPA render delay / slow network interface

**Fix path** → call `wait-strategy` skill or adjust timeout configuration

### Branch C: Assertion Issue

**Criteria:** `AssertionError`, element exists and is visible, but value/state doesn't match expectation

**Investigation steps:**
1. Get actual element text/attribute value, compare with expected value in test code
2. Determine cause: business data change / copy update / environment difference

**Fix path** → report the difference and suggest user decision (usually a business change rather than a code bug)

### Branch D: Page Structure Change

**Criteria:** `is_page_loaded()` fails or current URL doesn't match expectation

**Investigation steps:**
1. Use agent-browser to capture a full-page snapshot, batch-compare with PageObject locators
2. Determine cause: route change / page redesign / permission change causing redirect

**Fix path** → for small changes call `locator-replacer`; for large redesigns report to user, suggest `gen-page-test`

### Fallback Mechanism

If classification-based investigation yields no result, fall back to the previous level and reclassify. Maximum one fallback; if still unable to locate, compile collected information and report to user.

---

## Browser Tool Selection

DOM exploration/locator collection → agent-browser (preferred); precise verification/assertions → Playwright MCP; if agent-browser not installed → use Playwright MCP throughout (P0.4 fallback).

---

## Checklist

Before each quick-debug session ends, confirm:

- [ ] Root cause identified and classified (which branch A/B/C/D)
- [ ] Fix action executed (or reported to user for manual decision)
- [ ] In-place verification passed (fixed locator/wait is effective on current page)
- [ ] Suggested user re-run full tests to confirm regression
- [ ] For save operation verification failures, refer to [save-verify-strategy](../save-verify-strategy/) (Toast timing / redirect detection / data comparison)

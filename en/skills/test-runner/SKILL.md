---
name: test-runner
description: Run pytest + structured failure analysis. Trigger: run tests, run test, pytest, failure analysis, allure.
---

# Test Runner — Running Tests and Analyzing Results

> **⚠️ Must confirm `--env` with the user before running** (see [agent-behavior.md](../../rules/agent-behavior/agent-behavior.md) P0.2).
> Even if `config/settings.py::DEFAULT_ENV="prod"` or the examples below show `--env=<pre|prod>` (examples ≠ defaults), you must still ask the user.

## Pre-Run Preparation

```bash
# Confirm virtual environment is activated
source .venv/bin/activate

# Confirm dependencies are installed
pip list | grep -E "playwright|pytest|allure"
```

---

## Run Modes

All tests run against a real environment (URL + token).

### Mode 1: Single Story (Debugging / Locator Verification)

**Scenario:** Verify after replacing locators, debug a single page regression point

```bash
# Corresponding role
pytest tests/<role>/test_<role>_flow.py --env=<pre|prod> -v -k "test_xxx"
# Corresponding role
pytest tests/<role>/test_<role>_home.py --env=<pre|prod> -v -k "test_<case_name>"
```

### Mode 2: By Role / Full Regression

**Scenario:** Pre-release verification, complete regression

```bash
# Role A full regression
pytest tests/<roleA>/ --env=<pre|prod>
# Role B full regression
pytest tests/<roleB>/ --env=<pre|prod>
# Full regression
pytest tests/ --env=<pre|prod>
```

### View Allure Report

```bash
# Launch report server (available immediately after running tests)
allure serve reports/allure-results

# Generate static report (deployable)
allure generate reports/allure-results -o reports/allure-report --clean
```

---

## Result Analysis

### pytest Output Interpretation

```
tests/test_xxx.py::TestXxx::test_method PASSED    → passed
tests/test_xxx.py::TestXxx::test_method FAILED    → failed (needs analysis)
tests/test_xxx.py::TestXxx::test_method ERROR     → fixture/setup exception
tests/test_xxx.py::TestXxx::test_method SKIPPED   → skipped
```

### Failure Classification and Handling

After a run fails, diagnose by the following classification:

#### Type A: Locator Failure

**Signature:**
```
TimeoutError: Timeout 10000ms exceeded.
  waiting for locator("text=<feature name>")
```

**Action:** Trigger `locator-replacer` skill, use agent-browser to access the real page and re-extract locators (tool selection follows [agent-behavior P0.4](../../rules/agent-behavior/agent-behavior.md)).

#### Type B: Page Load Timeout

**Signature:**
```
TimeoutError: page.wait_for_load_state: Timeout 30000ms exceeded.
  waiting for "networkidle"
```

**Action:**
1. Check network connectivity (hosts config, VPN)
2. Check if token has expired
3. Increase `DEFAULT_TIMEOUT` (temporary measure)

#### Type C: Assertion Failure

**Signature:**
```
AssertionError: <Page Name> failed to load
assert False
```

**Action:**
1. Check if the page navigated to the correct target URL
2. Check if the `PAGE_IDENTIFIER` locator is still valid
3. Check if page content has changed due to a version update

#### Type D: Authentication Failure

**Signature:**
```
AssertionError: Token login failed
```

**Action:**
1. Check if the token in `config/settings.py` is valid
2. Check if the `--env` parameter is correct
3. Check if the local hosts file points to the correct server IP

#### 💡 Quick Debug Recommendation

When a failure needs deeper investigation (locator failure, page structure change, etc.), consider entering [quick-debug](../quick-debug/SKILL.md) mode: jump directly to the problem page via token login-free access, avoiding re-running the full flow from login.

---

## Result Summary Template

After a run completes, output a summary in the following format:

```
## Test Run Summary

**Run Mode:** Single story / Full main flow
**Environment:** pre / prod
**Time:** 2026-04-15 15:30

### Results

| Status | Count |
|------|------|
| PASSED | X |
| FAILED | X |
| ERROR | X |
| SKIPPED | X |

### Failure Details (if any)

| Test Case | Failure Type | Reason | Suggested Action |
|----------|---------|------|---------|
| test_xxx | A: Locator failure | text=xxx not unique | Use locator-replacer |
| test_yyy | D: Auth failure | token expired | Update settings.py |
```

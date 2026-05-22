---
paths:
  - "pages/**"
  - "tests/**"
---

# Performance API Cross-Test Isolation

**Trigger**: Using `performance.getEntriesByType('resource')` to collect API errors, count requests, or any scenario that asserts based on the Performance API.

---

## The Problem

`performance.getEntriesByType('resource')` returns a **cumulative list of all resource load records during the page's lifecycle**. In class-level shared context (same page running multiple test cases) scenarios:

```
Test A executes → API X returns 400 → performance records X
Test B executes → calls getEntriesByType → can still read Test A's X
→ Test B falsely reports "API errors exist"
```

Test B passes when run independently, but fails when run in batch — this is **cross-test contamination** caused by the Performance API's cumulative behavior.

---

## Rule: Clear Immediately After Collection

Every time `performance.getEntriesByType()` is used to collect data, **must call `performance.clearResourceTimings()` in the same evaluate call to clear the buffer**, ensuring the next collection only includes new records.

❌ Anti-pattern:

```python
def get_api_errors(self) -> list[dict]:
    entries = self.page.evaluate("""() => {
        return performance.getEntriesByType('resource')
            .filter(e => e.initiatorType === 'xmlhttprequest' || e.initiatorType === 'fetch')
            .map(e => ({ name: e.name, status: e.responseStatus || 0 }))
            .filter(e => e.status >= 400);
    }""")
    # ← no clearing; next call will still return these errors
    return entries
```

✅ Best practice:

```python
def get_api_errors(self) -> list[dict]:
    entries = self.page.evaluate("""() => {
        const errors = performance.getEntriesByType('resource')
            .filter(e => e.initiatorType === 'xmlhttprequest' || e.initiatorType === 'fetch')
            .map(e => ({ name: e.name, status: e.responseStatus || 0 }))
            .filter(e => e.status >= 400);
        performance.clearResourceTimings();
        return errors;
    }""")
    return entries
```

---

## Key Points

| Point | Description |
|------|------|
| Clear must be inside evaluate | Store result then clear, both in the same JS execution, avoiding race conditions |
| Affects the entire page | `clearResourceTimings()` clears all resource timing records for the current page, regardless of domain |
| Class-level shared context is high-risk | Same page runs N test cases; without clearing, errors accumulate N times |
| Function-level context is unaffected | Each test case has independent page, closed after use, naturally isolated |

---

## Diagnostic Signals

When the following symptoms appear, check Performance API isolation first:

1. **Passes when run individually, fails when run in batch** — classic cumulative contamination
2. **Failing test reports API errors it didn't trigger** — errors came from previous test cases
3. **Later test cases in the same class fail more often** — more accumulated error records

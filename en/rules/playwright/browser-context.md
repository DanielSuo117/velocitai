---
paths:
  - "conftest.py"
  - "tests/**/base_test.py"
  - "tests/**/*_base_test.py"
---

# Browser Context

**Trigger**: When designing fixture scope and deciding the range of context sharing.

## Authentication Mechanism

- Authentication is completed via URL token, executed independently by `BaseTest._login_setup` for each test
- Each test case gets an independent **context + page** (managed by `conftest.py`'s `page` fixture)
- **Do not** manually manage browser lifecycle in tests

---

## Forbidden: Session-Level Shared Context (Cross-Domain Cookie Contamination)

❌ Anti-pattern:

```python
@pytest.fixture(scope="session")
def authenticated_context(browser, token):
    context = browser.new_context()
    yield context   # all tests share; after navigating to different domains, cookie contamination
```

✅ Best practice:

```python
@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    yield page
    page.close()
    context.close()
```

**Reason**: Different roles use different domains; sharing context causes cross-domain cookie contamination.

---

## Exception: Same-Domain Class-Level Sharing Is Allowed

Class-level sharing is permitted when all of the following conditions are met:
1. All test cases in the class are under the **same domain** and **do not navigate to another endpoint**
2. Managed by a class-scope fixture; context auto-closes when the class ends
3. Each test case has a reset logic to eliminate implicit coupling

**Forbidden**: session-level cross-class sharing; cross-domain within the same class.

✅ Best practice: `<Role>BaseTest` class-level sharing

```python
class RoleBaseTest(BaseTest):
    @pytest.fixture(scope="class", autouse=True)
    def _role_context(self, class_page, token, request):
        ...  # login + switch to corresponding role; class test cases share class_page
```

❌ Anti-pattern: navigate back to another role's domain within a role class

```python
def test_bad(self):
    self.<role>_home.click_return_to_<other_role>()  # contaminates class shared context
```

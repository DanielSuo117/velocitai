---
paths:
  - "conftest.py"
  - "tests/**/base_test.py"
  - "tests/**/*_base_test.py"
---

# 浏览器上下文

**触发**：设计 fixture 作用域、决定 context 共享范围时。

## 认证机制

- 认证通过 URL token 完成，由 `BaseTest._login_setup` 每个测试独立执行
- 每个用例获取独立 **context + page**（`conftest.py` 的 `page` fixture 管理）
- **不要**在测试中手动管理浏览器生命周期

---

## 禁止 session 级共享 context（跨域 cookie 污染）

❌ 反例：

```python
@pytest.fixture(scope="session")
def authenticated_context(browser, token):
    context = browser.new_context()
    yield context   # 所有测试共享，跳转不同域名后 cookie 污染
```

✅ 正例：

```python
@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    yield page
    page.close()
    context.close()
```

**原因**：不同角色使用不同域名，共享 context 会导致跨域 cookie 污染。

---

## 例外：同域 class 级共享允许

满足以下条件时可用 class 级共享：
1. class 内所有用例在**同一域名**下，**不跳回其他端**
2. 由 class-scope fixture 管理，class 结束自动 `context.close()`
3. 每个用例有复位逻辑消除隐性耦合

**禁止**：session 级跨 class 共享、同一 class 内跨域。

✅ 正例：`<Role>BaseTest` class 级共享

```python
class RoleBaseTest(BaseTest):
    @pytest.fixture(scope="class", autouse=True)
    def _role_context(self, class_page, token, request):
        ...  # 登录 + 切换到对应角色；class 内用例共用 class_page
```

❌ 反例：在某角色 class 内跳回另一角色域名

```python
def test_bad(self):
    self.<role>_home.click_return_to_<other_role>()  # 污染 class 共享 context
```

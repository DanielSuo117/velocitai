# 同 class 内跨用例 page 接力模式

> 由 [architecture](../SKILL.md) 按需加载。仅当需要在同一 class 的多个用例间接力同一页面状态时才读。

**场景**：同一 class 的多个用例形成**线性流程链**，后一个用例的起点是前一个用例的终点，不必从头登录。

```
test_a（搜索课程）
    ↓ 页面停留在搜索结果
test_b（点击课程 → 新 tab 打开课程首页）
    ↓ 新 tab 保存为 class 属性
test_c（在课程首页继续操作）
    ↓ 直接使用 class 属性中的 page
```

### 实现要点

1. **class-scope fixture 完成一次性登录**：覆盖父类 `_login_setup` 为 no-op，用 `class_page` + `request.cls.page` 共享
2. **用例间 page 接力**：当用例打开新 tab 时，将新 page 保存到 class 属性（`type(self).<attr> = new_page`），后续用例通过 `self.<attr>` 访问
3. **新 tab 不关闭**：接力链中的 page 保持打开，直到 class 结束 context 自动销毁
4. **用例顺序即流程顺序**：pytest 默认按文件中方法出现顺序执行

### 骨架

> `class_page` fixture 的实现见 [browser-config](../../browser-config/SKILL.md) "Fixture 分层模板"。

```python
class TestSomeFlow(BaseTest):

    @pytest.fixture(autouse=True)
    def _login_setup(self):
        yield  # no-op，覆盖父类

    @pytest.fixture(scope="class", autouse=True)
    def _shared_setup(self, class_page, token, request):
        login_page = LoginPage(class_page)
        login_page.login_with_token(BASE_URL, token)
        request.cls.page = class_page

    def test_step_1(self):
        ...  # self.page 已由 _shared_setup 注入，class 级共享

    def test_step_2(self):
        new_page = some_page.click_open_new_tab()
        type(self).detail_page = new_page  # 保存到 class 属性供后续用例

    def test_step_3(self):
        detail = SomeDetailPage(self.detail_page)  # 直接接力
        ...
```

### 适用条件

- ✅ 同一 class 内、用例具有明确的先后依赖关系
- ✅ 新 tab 仍在同域或已携带认证（无需二次登录）
- ❌ 如果用例间无依赖关系，不要用接力模式（改用独立 function-scope page）

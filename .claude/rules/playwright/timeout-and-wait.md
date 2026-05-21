---
paths:
  - "pages/**"
  - "tests/**"
  - "conftest.py"
---

# 超时排查 & 等待策略

---

## 一、超时失败排查：先确认"在哪个页面"，再排查"定位符对不对"

**触发**：`wait_for_element` / `is_visible` / `inner_text` 等操作报 `TimeoutError`。

**规则**：超时失败时，**第一步**永远是确认当前 page 对象指向的页面是否正确，**禁止**直接改定位符。

90% 的超时问题不是"元素找不到"，而是"根本不在目标页面上"。常见原因：
1. 按钮打开了**新 tab**，代码还在旧 tab 的 page 对象上等（最常见）
2. SPA 路由没跳转（前一步操作被下拉框/弹窗拦截，点击没生效）
3. 页面被重定向到登录页（token 过期、跨域认证失败）

**排查顺序（必须严格按序）**：

```
TimeoutError
   │
   ▼
① 打印 page.url 和 page.title()
   │  → URL 不对 → 页面没跳转，排查上一步的点击是否生效
   │  → URL 正确 → 进入 ②
   ▼
② 检查是否有新 tab 打开（context.pages 数量变化）
   │  → 多了新 tab → 目标内容在新 tab 里，当前 page 是旧的
   │  → 没有新 tab → 进入 ③
   ▼
③ 此时才排查定位符问题（page.locator("xxx").count()）
```

❌ 反例：超时就换定位符，换了 4 次全部超时，根因是新 tab。

✅ 正例：

```python
print(f"当前 URL: {page.url}")
print(f"当前标题: {page.title()}")
print(f"context 中 page 数量: {len(page.context.pages)}")
```

---

## 二、等待策略

**触发**：编写 fixture / PageObject 中涉及页面导航或 SPA 模块切换的等待逻辑时。

**规则**：全局隐式等待 + 仅慢路径显式 timeout。完整策略 → [wait-strategy skill](../../skills/wait-strategy/SKILL.md)

### SPA 菜单/Tab 切换后 `networkidle` 不等于渲染完成

在 Vue / React 等 SPA 框架中，点击菜单切换模块后，`networkidle` 只能保证网络请求完成，**不能保证组件已渲染到 DOM**。

**规则**：SPA 菜单/Tab 切换后，若下一步依赖新渲染元素，必须在 `networkidle` 后额外加 `wait_for_timeout(3000)` 或 `wait_for_element()` 确认稳定。

❌ 反例：

```python
def _setup_context(self, ...):
    home.click_target_menu()
    assert home.is_target_section_visible()
    home.search("<搜索关键词>")               # 搜索框正在被 Vue 重渲染
```

✅ 正例：

```python
def _setup_context(self, ...):
    home.click_target_menu()
    assert home.is_target_section_visible()
    self.<role>_page.wait_for_timeout(3000)   # 等待异步组件渲染完成
    home.search("<搜索关键词>")
```

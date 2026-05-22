---
# 不自动加载。由 agent-behavior.md P0.4 按需引用。
---

# 浏览器工具使用规则（P0.4 系列详细反例/正例）

> 工具选型总则见 [agent-behavior.md](./agent-behavior.md) P0.4

---

## P0.4.1 · agent-browser click 失败立即降级到 eval

**触发**：`agent-browser click @ref` 一次无反应（无跳转 / 无 UI 变化）。

**原因**：`agent-browser click` 基于 CDP 无障碍树。对非语义化 `<div>` / `<span>` + 前端框架事件绑定（Vue `@click`、React `onClick`），CDP 点击有时无法触发合成事件。

**规则**：一次无反应立即降级到 JS 点击，禁止反复重试。

✅ 正例：

```bash
agent-browser click @e27   # 没反应
# 立即降级到 JS 点击
agent-browser eval "(function(){ document.querySelectorAll('.target-selector')[0].click(); })()"
```

---

## P0.4.2 · agent-browser 触发新 tab 后必须手动切换

**触发**：`agent-browser click` 或 `eval` 触发了新 tab。

**规则**：agent-browser 不会自动切换到新 tab。操作后必须 list → 切换 → snapshot。

✅ 正例：

```bash
agent-browser click @e11
agent-browser tab list            # 确认新 tab
agent-browser tab t2              # 切换
agent-browser snapshot -i -c      # 新页面内容
```

---

## P0.4.2.1 · Playwright MCP 跨子域 SSO 免登：必须等 networkidle 再跳转

**触发**：用 Playwright MCP 调试需要 SSO 认证的子域名页面。

**原因**：`browser_navigate` 不等 `networkidle`，token 登录后 SSO cookie 可能还在异步写入，直接跳转子域名时 cookie 未就绪 → 被重定向到登录页。

**规则**：token 免登后，必须用 `browser_wait_for` 确认登录成功标识出现，再导航到子域名。

✅ 正例：

```
browser_navigate → <BASE_URL>/entry?token=JWT
browser_wait_for → text="<登录成功标识>"      # 确认登录完成
browser_navigate → <TARGET_SUBDOMAIN>/...
browser_wait_for → text="<目标页特征文本>"    # 确认子域名页面加载
```

**仍然失败时的降级方案**：用独立 Python 脚本显式调用 `wait_for_load_state("networkidle")`：

```python
page.goto(f"{BASE_URL}/entry?token={TOKEN}")
page.wait_for_load_state("networkidle")
page.goto(TARGET_URL)
page.wait_for_load_state("networkidle")
```

---

## P0.4.3 · 编写新用例前必须验证现有定位符

**触发**：为已有 PageObject 新增用例或扩展方法时。

**原因**：页面会迭代更新，已有定位符可能失效。

**规则**：用 `agent-browser` 打开真实页面验证目标区域的现有定位符。发现不匹配时：修正定位符 → 同步更新 `docs/regression-points.md` → 检查其他用例引用。

✅ 正例：

```bash
agent-browser open <页面URL>
agent-browser snapshot -s "<目标容器选择器>"
# 确认实际文本与代码中定位符一致，不一致则先修正再写用例
```

---

## P0.4.4 · 批量多视图采集用 eval 循环，不逐个手动交互

**触发**：需采集多个 tab / 菜单项 / 面板内容（N ≥ 3）。

**规则**：用 JS eval 循环批量采集，禁止逐个 click + snapshot（N 个元素 = 2N 条命令）。

✅ 正例：

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

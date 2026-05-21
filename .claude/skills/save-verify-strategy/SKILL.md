---
name: save-verify-strategy
description: 表单保存后验证（Toast / 重定向 / 数据对比 / 富文本清空）。触发：保存验证、toast、重定向检测、Meta+A、保存成功判断。
---

# 表单保存验证策略

---

## 一、macOS 富文本编辑器全选必须用 Meta+A

macOS Chromium 中 `Control+A` 是 Emacs 快捷键（光标移到行首），**不是**"全选"。在 CKEditor / TinyMCE / Quill 等富文本编辑器中，`Control+A` 无法选中全部内容，导致旧内容残留。

❌ 反例：

```python
def fill_rich_text(self, text: str):
    self.click(self.EDITOR)
    self.page.keyboard.press("Control+A")   # macOS 上只移动光标到行首
    self.page.keyboard.press("Backspace")   # 只删一个字符，旧内容残留
    self.page.keyboard.type(text)           # 新内容追加在旧内容后面
```

✅ 正例：

```python
def fill_rich_text(self, text: str):
    self.click(self.EDITOR)
    self.page.keyboard.press("Meta+A")      # macOS Command+A = 全选
    self.page.keyboard.press("Backspace")   # 清空全部内容
    self.page.keyboard.type(text)           # 写入纯新内容
```

**排查信号**：填入的数据末尾多了旧内容残片（如 `"2026-05-06 10:30:00123"` 尾部多了 `123`）→ 全选快捷键无效。

---

## 二、保存后验证策略：三级选择

| 保存后行为 | 验证方式 | 可靠性 | 适用场景 |
|-----------|---------|--------|---------|
| 显示 Toast | `is_visible(toast_locator)` — 必须在 networkidle 后**立即**检测 | 低（2-3s 消失） | 有明确 Toast 的场景 |
| 页面重定向 | 检测编辑页特征元素消失 `wait_for(state="hidden")` | 中（持久状态） | 保存后自动跳转的场景 |
| 无 UI 反馈 | 写入标记数据 → 重新打开 → 读取对比 | 高（数据级验证） | 无 Toast、不确定是否重定向 |

**原则**：三级可组合使用。优先用持久状态变更，Toast 仅作辅助。

### 2.1 Toast 时序陷阱

`click_save()` 方法中的 `wait_for_timeout()` 会消耗 Toast 存活时间。**必须**在 networkidle 后立即检测 Toast，不能先等待再检测。

❌ 反例：

```python
def click_save(self):
    self.click(self.SAVE_BTN)
    self.page.wait_for_load_state("networkidle")
    self.page.wait_for_timeout(3000)   # Toast 在这 3s 内出现又消失了

# 调用方
assert page.is_visible(toast)          # Toast 已消失，永远 False
```

✅ 正例：

```python
def click_save(self):
    self.click(self.SAVE_BTN)
    self.page.wait_for_load_state("networkidle")
    # 不加额外等待 — 让调用方立即检测 Toast

# 调用方
is_ok = page.is_visible(toast, timeout=10000)   # 立即开始等 Toast
page.wait_for_timeout(3000)                      # 检测完再等页面稳定
```

### 2.2 重定向检测

保存后页面可能重定向离开编辑页。通过检测编辑页**特征元素消失**来确认保存成功：

```python
def is_save_success(self) -> bool:
    """编辑页 header 消失 = 保存成功并已离开编辑页"""
    try:
        self.page.locator(self.EDIT_PAGE_HEADER).first.wait_for(
            state="hidden", timeout=15000
        )
        return True
    except Exception:
        return False
```

### 2.3 重定向目的地不可假设

保存后的重定向目的地可能因**导航上下文**不同而异（直接 URL 访问 vs SPA 内跳转 vs 新 tab 中操作）。不要断言重定向到某个特定页面。

❌ 反例：

```python
# 假设保存后一定重定向到首页
redirected_home = HomePage(page)
assert redirected_home.is_page_loaded()   # 实际可能跳到其他页面
```

✅ 正例：

```python
# 只验证离开了编辑页，不假设去了哪里
assert edit_page.is_save_success()        # 编辑页 header 消失 = 保存成功
```

---

## 三、多 tab 保存后：关闭旧 tab，从原始 tab 重入

保存后如果需要重新访问同一页面验证数据，**不要**尝试在重定向后的页面内导航（重定向目的地不确定，元素可能不存在）。关闭旧 tab，从原始 tab（状态稳定）重新打开新 tab 进入。

❌ 反例：

```python
# 保存后尝试在重定向页面内导航回去
redirected_page = SomePage(new_page)
assert redirected_page.is_page_loaded()    # 重定向目的地不确定 → 失败
redirected_page.click(breadcrumb)          # 元素可能不存在
```

✅ 正例：

```python
# 保存后关闭旧 tab
finally:
    new_page.close()

# 原始 tab 状态稳定，从这里重新进入
assert original_home.is_page_loaded()
new_page_2 = original_home.open_target_in_new_tab(name)
try:
    # 在新 tab 中导航到编辑页 → 验证数据
finally:
    new_page_2.close()
```

---

## 四、数据对比验证模式（最终验证）

当没有 Toast 或 UI 反馈时，用「写入标记 → 保存 → 重新打开 → 读取对比」作为最终验证闭环。

```python
# ── 写入阶段 ──
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
edit_page.fill_description(timestamp)
write_test_data("标记键名", timestamp)          # 持久化到配置文件

# ... 保存操作 ...

# ── 验证阶段（重新打开编辑页）──
saved = read_test_data().get("标记键名")
actual = edit_page.get_description_text()
allure.attach(saved, name="期望时间戳", ...)     # 无论成败都记录到报告
allure.attach(actual, name="实际时间戳", ...)
assert actual == saved, (
    f"数据不一致：期望='{saved}'，实际='{actual}'"
)
```

**关键要点**：
1. 标记数据必须**写入配置文件**（跨用例共享，非内存变量），便于后续用例复用
2. 无论断言成败，都用 `allure.attach()` 将期望值和实际值写入报告
3. 断言失败信息必须包含**两个值的对比**，方便排查


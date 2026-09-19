---
name: save-verify-strategy
description: 表单保存后验证（Toast / 重定向 / 数据对比 / 富文本清空）。触发：保存验证、toast、重定向检测、Meta+A、保存成功判断。
---

# 表单保存验证策略

---

## 一、macOS 富文本编辑器全选

macOS 上富文本编辑器的全选按键差异（Control+A 无效）→
[references/macos-select-all.md](./references/macos-select-all.md)

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

保存动作发生在新开 tab 中时的处理 →
[references/multi-tab-reentry.md](./references/multi-tab-reentry.md)

## 四、数据对比验证模式（最终验证）

保存前后做数据比对的实现方式 →
[references/data-comparison.md](./references/data-comparison.md)

# macOS 富文本编辑器全选必须用 Meta+A

> 由 [save-verify-strategy](../SKILL.md) 按需加载。在 macOS 上操作富文本编辑器时才读。

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

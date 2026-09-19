# 数据对比验证模式（最终验证）

> 由 [save-verify-strategy](../SKILL.md) 按需加载。需要做保存前后数据比对时才读。

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

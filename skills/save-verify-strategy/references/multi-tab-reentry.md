# 多 tab 保存后：关闭旧 tab，从原始 tab 重入

> 由 [save-verify-strategy](../SKILL.md) 按需加载。保存动作发生在新开 tab 中时才读。

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

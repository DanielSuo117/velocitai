---
paths:
  - "pages/**"
  - "tests/**"
---

# Performance API 跨用例隔离

**触发**：使用 `performance.getEntriesByType('resource')` 收集接口错误、统计请求数量，或任何基于 Performance API 做断言的场景。

---

## 问题

`performance.getEntriesByType('resource')` 返回的是**页面生命周期内所有资源加载记录的累积列表**。在 class 级共享 context（同一个 page 跑多个用例）场景下：

```
用例 A 执行 → 接口 X 返回 400 → performance 记录了 X
用例 B 执行 → 调用 getEntriesByType → 仍然能读到用例 A 的 X
→ 用例 B 误报"存在接口错误"
```

单独执行用例 B 通过，批量执行时用例 B 失败 — 这是 Performance API 累积特性导致的**跨用例污染**。

---

## 规则：收集后立即清空

每次通过 `performance.getEntriesByType()` 收集数据后，**必须在同一次 evaluate 中调用 `performance.clearResourceTimings()` 清空缓冲区**，确保下一次收集只包含新增记录。

❌ 反例：

```python
def get_api_errors(self) -> list[dict]:
    entries = self.page.evaluate("""() => {
        return performance.getEntriesByType('resource')
            .filter(e => e.initiatorType === 'xmlhttprequest' || e.initiatorType === 'fetch')
            .map(e => ({ name: e.name, status: e.responseStatus || 0 }))
            .filter(e => e.status >= 400);
    }""")
    # ← 没有清空，下一次调用仍会返回这些错误
    return entries
```

✅ 正例：

```python
def get_api_errors(self) -> list[dict]:
    entries = self.page.evaluate("""() => {
        const errors = performance.getEntriesByType('resource')
            .filter(e => e.initiatorType === 'xmlhttprequest' || e.initiatorType === 'fetch')
            .map(e => ({ name: e.name, status: e.responseStatus || 0 }))
            .filter(e => e.status >= 400);
        performance.clearResourceTimings();
        return errors;
    }""")
    return entries
```

---

## 关键点

| 要点 | 说明 |
|------|------|
| 清空必须在 evaluate 内部 | 先存结果再清空，在同一次 JS 执行中完成，避免竞态 |
| 影响范围是整个 page | `clearResourceTimings()` 清空的是当前 page 的所有 resource timing 记录，不区分域名 |
| class 级共享 context 是高危场景 | 同一个 page 跑 N 个用例，不清空就会 N 倍累积 |
| function 级 context 不受影响 | 每个用例独立 page，用完就关闭，天然隔离 |

---

## 排查信号

遇到以下现象时，首先检查 Performance API 隔离：

1. **单独跑通过，批量跑失败** — 典型的累积污染
2. **失败用例报的接口错误不是自己触发的** — 错误来自前面的用例
3. **同一个 class 内越靠后的用例越容易失败** — 累积的错误记录越多

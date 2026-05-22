---
name: case-round-trip
description: 共享 page 下用例离开起点后必须 UI 返回并断言。触发：往返闭合、case round trip、复位超时、scope 共享 page。
---

# Case Round Trip — 用例往返闭合

> 仅适用 Playwright + pytest。

## 核心规则

共享 page（scope > function 的 fixture）下，**用例离开起点页后必须在末尾通过真实 UI 返回并断言**；不要在复位 fixture 里做 goto 兜底。

## 何时适用

- 多个用例共享一个 page / browser context（class/module/session scope）
- 用例会进入"脱离门户布局"的页面（子路由、沉浸式页面、跨子域）
- 复位 fixture 依赖门户布局才有的元素（侧边栏 / 顶部 nav）

## 做法

1. 给每个会"脱离门户布局"的 PageObject 加 `click_back_to_<landing>()`，走真实 UI 返回按钮
2. 用例主断言后显式调用返回方法，并再次断言起点页加载
3. 复位 fixture 保持最简单形态（仅走门户导航），不做 goto 兜底

```python
def test_enter_detail(self):
    self.home.click_first_item()
    detail = DetailPage(self.page)
    assert detail.is_page_loaded(), "详情页未加载"

    detail.click_back_to_home()
    assert self.home.is_page_loaded(), "返回起点页失败"
```

## 起点 is_page_loaded 的严格判据

复位 fixture 通常判断 `if not start.is_page_loaded(): start.click_back_to_landing()`。若 `is_page_loaded()` 仅校验"页面骨架可见"（title / 容器），切到其他 tab/子路由后骨架仍在 → 返回 True → 复位永不触发 → 下一用例起点错乱。

**规则：起点 PageObject 的 `is_page_loaded()` 必须包含"当前停留在起点状态"判据**（起点 tab 激活态 / 起点 URL / 起点独有内容），而不仅是"骨架存在"。

```python
# ❌ 只校验骨架 — 切到其他 tab 后仍返回 True，复位失效
def is_page_loaded(self) -> bool:
    return self.is_visible(self.PAGE_TITLE) and self.is_visible(self.TAB_BAR)

# ✅ 加"当前在起点 tab"判据 — tab 切换后返回 False，触发复位
def is_page_loaded(self) -> bool:
    return (
        self.is_visible(self.PAGE_TITLE)
        and self.is_visible(self.TAB_BAR)
        and self.is_visible(self.LANDING_TAB_ACTIVE_MARK)   # 关键第 3 条
    )
```

`LANDING_TAB_ACTIVE_MARK` 的 selector 必须用 text= 等锁定到**具体起点 tab**（如 `.tab.active >> text=<起点 tab 名>`），否则 `.active` 会匹配任意激活 tab，同样失效（见 [locator-strategy.md 状态类 selector 必须配 text 锁定](../../rules/playwright/locator-strategy.md)）。

## 决策

```
跳转目标是否仍保留起点页的门户导航？
├─ 是 → 依赖复位 fixture 即可
└─ 否 → PageObject 必须提供返回方法 + 用例末尾显式返回 + 断言
```

## ❌ 反例

- 进入沉浸式页面后只断言进入，不返回 → 后续用例复位 fixture 点不到门户导航
- `page.goto(<landing_url>)` 绕过返回按钮 → 失去对返回按钮的回归覆盖
- `if not visible: goto(...)` 塞进复位 fixture → 掩盖"用例未闭合"真问题

## 检查清单

- [ ] 跳转目标脱离门户布局 → 本规则适用
- [ ] PageObject 提供 `click_back_to_<landing>()`
- [ ] 用例末尾调用返回方法并断言起点页加载
- [ ] 测试顺序打乱仍全部通过

---

## 项目落地参考

项目中脱离门户布局的 PageObject（需实现 `click_back_to_<landing>`）见 [docs/pages-catalog.md](../../../docs/pages-catalog.md) 与 [docs/regression-points.md](../../../docs/regression-points.md)（带"⚠️ 跳转目标脱离门户布局"标注的页面）。

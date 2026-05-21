---
name: wait-strategy
description: 隐式等待为主、显式等待仅慢路径。触发：等待策略、timeout、wait、隐式等待、显式等待。
---

# 等待策略 — 隐式等待为主，显式等待为辅

## 核心原则

**隐式等待覆盖 99% 场景，显式等待仅用于已知的慢路径。**

---

## 一、隐式等待（默认，全局生效）

### 什么是隐式等待

通过 `page.set_default_timeout(ms)` 在 page 创建后立即设置。此后该 page 上所有 Playwright 操作（`click`、`fill`、`locator.wait_for`、`is_visible` 等）自动等待元素就绪，超时前持续重试，无需逐个调用指定 timeout。

### 配置位置

隐式等待的超时时长统一声明在配置文件中（如 `DEFAULT_TIMEOUT` 常量），在 fixture 层注入到每个 page 实例：

```python
# 配置文件
DEFAULT_TIMEOUT = 15000   # 15 秒，兼顾网络波动

# fixture 层（function 级 / class 级均需设置）
page = context.new_page()
page.set_default_timeout(DEFAULT_TIMEOUT)
```

### 推荐时长

| 环境 | 推荐值 | 说明 |
|------|--------|------|
| 内网 / CI | 10000 (10s) | 网络稳定，无需长等 |
| 外网 / 生产 | 15000 (15s) | 兼顾偶发网络波动 |
| 弱网测试 | 20000~30000 | 专项弱网场景 |

---

## 二、显式等待（仅用于特殊场景）

### 什么时候用

| 场景 | 原因 | 做法 |
|------|------|------|
| 大文件上传 / 导入 | 服务器处理耗时远超常规页面操作 | `self.is_visible(LOCATOR, timeout=60000)` |
| 长轮询 / 异步任务回调 | 后端处理完才刷新前端状态 | `page.locator(...).wait_for(state="visible", timeout=30000)` |
| 第三方服务跳转 | OAuth / 支付等外部页面响应不可控 | `page.wait_for_url("**/callback**", timeout=30000)` |
| 首次冷启动 | 服务刚部署、首次请求慢 | 对首个导航操作单独加大 timeout |

### 使用方式

在**调用处**传入显式 timeout，覆盖隐式默认值：

```python
# BasePage 封装方法支持 timeout 参数
def is_visible(self, locator, timeout=DEFAULT_TIMEOUT) -> bool:
    ...

# 用例中：仅对已知慢操作显式指定
def test_upload_large_file(self):
    self.page_obj.click_upload()
    assert self.page_obj.is_visible(
        self.page_obj.UPLOAD_SUCCESS_INDICATOR,
        timeout=60000   # 显式等待 60 秒，仅此一处
    ), "大文件上传超时"
```

### 禁止事项

- **禁止 `time.sleep()` 硬等待** — Playwright 的自动等待机制已覆盖，硬等待浪费时间且不可靠
- **禁止给每个操作都加显式 timeout** — 这等于放弃了隐式等待的统一管理优势
- **禁止在 PageObject 方法内部硬编码超长 timeout** — 超时值应由调用方（用例层）按场景决定

---

## 三、`wait_for_load_state` 与隐式等待的关系

`page.wait_for_load_state("networkidle")` 是**导航级等待**，与元素级隐式等待互补，不冲突：

| 等待类型 | 作用层级 | 触发时机 | 受 `set_default_timeout` 控制 |
|----------|---------|---------|------------------------------|
| `wait_for_load_state` | 导航 / 网络 | 页面跳转、AJAX 批量请求后 | 受 `set_default_navigation_timeout` 控制 |
| 隐式等待 | 元素 | 每次元素操作前 | 是 |

推荐模式：

```python
def click_navigate_to_target(self):
    self.click(self.TARGET_LINK)
    self.page.wait_for_load_state("networkidle")  # 等网络请求完成
    # 之后的 is_visible / click 等操作由隐式等待兜底
```

---

## 检查清单

- [ ] 全局 `DEFAULT_TIMEOUT` 已在配置文件统一声明
- [ ] 所有 page fixture（function 级 / class 级）均调用了 `page.set_default_timeout()`
- [ ] PageObject 业务方法中无 `time.sleep()`
- [ ] 显式 timeout 仅出现在已知慢路径的调用处，而非 PageObject 内部
- [ ] PageObject 的 `is_visible()` 等方法保留 `timeout` 参数供调用方覆盖

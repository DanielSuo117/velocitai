"""pages 包。

BasePage 采用惰性导出（PEP 562）：`from pages import BasePage` 行为不变，
但 `import pages.self_heal` 不再被动拉起 Playwright —— 自愈引擎是纯逻辑层，
必须能在没有浏览器的环境里单测。
"""

__all__ = [
    "BasePage",
]


def __getattr__(name):
    if name == "BasePage":
        from pages.base_page import BasePage
        return BasePage
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

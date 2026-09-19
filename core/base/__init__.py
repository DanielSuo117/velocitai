"""PO 基类层 —— 公共能力在此封装，业务代码继承即可。

惰性导出（PEP 562）：使 `core.healing` 等纯逻辑模块可在没有 Playwright 的
环境里被单测，而不会因为导入 core.base 被动拉起浏览器依赖。
"""

__all__ = ["BasePage", "BaseComponent", "BaseTest"]


def __getattr__(name):
    if name == "BasePage":
        from core.base.base_page import BasePage
        return BasePage
    if name == "BaseComponent":
        from core.base.base_component import BaseComponent
        return BaseComponent
    if name == "BaseTest":
        from core.base.base_test import BaseTest
        return BaseTest
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

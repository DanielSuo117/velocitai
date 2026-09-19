"""可复用 UI 组件的基类。

用途：弹窗、表格、下拉框这类在多个页面重复出现的片段。把它们做成组件，
比在每个页面对象里复制一遍定位符更容易维护 —— 组件改版时只改一处。

组件与页面对象共享同一套定位能力（含自愈），因此复用 BasePage 的实现，
只是把定位范围收窄到 root 之内。
"""
from __future__ import annotations

from playwright.sync_api import Page

from core.base.base_page import BasePage


class BaseComponent(BasePage):
    """作用域受限的页面对象。

    root 是组件在页面中的根节点选择器，组件内部的定位都相对它进行 ——
    这样同一个组件出现多次时（例如列表里的多行操作区）不会互相串台。
    """

    ROOT = ""     # 子类覆盖：组件根节点选择器

    def __init__(self, page: Page, root: str | None = None):
        super().__init__(page)
        self.root = root or self.ROOT
        if not self.root:
            raise ValueError(f"{type(self).__name__} 必须提供 ROOT 或 root 参数")

    def scope_root(self) -> str:
        """组件内的定位一律相对 root 进行。

        只需覆盖这一个方法：基类的每一处 locator 构造（_locate 与 _act）都
        经由它带上作用域，自愈的快照采集与唯一性判定同样收窄到 root 之内 ——
        越界修复正是「顶替到无关元素」的典型路径。

        曾经这里覆盖的是 _locate()，结果 click/fill 这些走 _act() 的操作
        完全绕开了它，组件的作用域形同虚设。作用域必须收口在一处。
        """
        return self.root

    def is_present(self) -> bool:
        return self.page.locator(self.root).count() > 0

    def is_page_loaded(self) -> bool:
        """组件以「根节点存在」作为加载完成的判定。"""
        return self.is_present()

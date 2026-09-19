"""组件作用域回归测试 —— 守住「组件定位不越出 root」这条线。

本文件存在的理由是一个真实缺陷：BaseComponent 只覆盖了 _locate()，而 click /
fill 这些操作走的是 _act()，**完全绕过那个覆盖**。结果 Dialog(ROOT=".modal")
调 click(".btn-ok") 时实际在整页找 .btn-ok —— 页面主区恰好也有一个同名按钮时
就点错了，且自愈关闭也照样错。

自愈开启时后果更重：快照会采到 root 之外的元素，把组件的定位符「修」成页面
别处的一个无关元素。越界修复正是「顶替到无关元素」的典型路径。

运行：python3 -m unittest discover -s framework/tests/unit -t framework
"""
import sys
import types
import unittest

try:  # pragma: no cover —— 无浏览器环境下补类型符号，判定逻辑可脱离 Playwright 验证
    import playwright.sync_api  # noqa: F401
except ImportError:  # pragma: no cover
    _stub = types.ModuleType("playwright.sync_api")
    _stub.Page = object
    _stub.Locator = object
    sys.modules.setdefault("playwright", types.ModuleType("playwright"))
    sys.modules.setdefault("playwright.sync_api", _stub)

from core.base.base_component import BaseComponent   # noqa: E402
from core.base.base_page import BasePage             # noqa: E402
from core.healing import runtime                     # noqa: E402

FINGERPRINT = {"tag": "button", "role": "button", "name": "确定"}
# 组件内真正的替代元素
INSIDE = '[data-testid="ok"]'
# root 之外、与指纹同样吻合的元素。越界自愈就会顶替到它。
OUTSIDE = '[data-testid="page-ok"]'


def _el(testid):
    return {"tag": "button", "attrs": {"data-testid": testid}, "role": "button",
            "name": "确定", "text": "确定", "classes": []}


class _Locator:
    def __init__(self, selector, page):
        self.selector, self._page = selector, page
        self.first = self

    def count(self):
        return 1

    def is_visible(self):
        return True

    def evaluate(self, js):
        return dict(FINGERPRINT, text="确定", classes=[])

    def click(self, **kwargs):
        self._page.clicked.append(self.selector)
        if self._page.broken and self.selector.endswith(".btn-ok"):
            raise RuntimeError(
                f"Timeout 15000ms exceeded. waiting for locator('{self.selector}')")
        return self.selector


class _Page:
    """broken=组件内原选择器已失效，需要自愈。"""

    url = "http://t/"

    def __init__(self, broken=False):
        self.broken = broken
        self.clicked = []
        self.snapshot_roots = []

    def locator(self, selector):
        return _Locator(selector, self)

    def evaluate(self, js, arg=None):
        if "querySelectorAll" in js:
            self.snapshot_roots.append(arg)
            # 真实的 root 作用域由浏览器实现；这里按约定模拟：
            # 传了 root 就只看得见组件内的元素，没传就整页可见。
            return [_el("ok")] if arg else [_el("ok"), _el("page-ok")]
        return FINGERPRINT


class _Dialog(BaseComponent):
    ROOT = ".modal"               # P0: 弹窗根节点
    OK_BTN = ".btn-ok"            # P0: 确定按钮


class TestComponentScope(unittest.TestCase):
    """自愈关闭时的作用域 —— 这与自愈无关，坏了就是组件层坏了。"""

    def test_click_stays_inside_root(self):
        page = _Page()
        _Dialog(page).click(".btn-ok")
        self.assertEqual(page.clicked, [".modal >> .btn-ok"],
                         "组件的 root 作用域丢失，操作会跑到整页去找元素")

    def test_locate_stays_inside_root(self):
        page = _Page()
        self.assertEqual(_Dialog(page)._locate(".btn-ok").selector,
                         ".modal >> .btn-ok")

    def test_count_stays_inside_root(self):
        """get_element_count 走 _locate 而非 _act，同样必须带作用域。"""
        page = _Page()
        _Dialog(page).get_element_count(".row")
        self.assertEqual(_Dialog(page)._locate(".row").selector, ".modal >> .row")

    def test_root_argument_overrides_class_constant(self):
        page = _Page()
        _Dialog(page, root="#dlg-2").click(".btn-ok")
        self.assertEqual(page.clicked, ["#dlg-2 >> .btn-ok"])

    def test_page_object_scope_is_empty(self):
        """整页对象不得被加上任何前缀 —— 逐字等价于直接 locator()。"""
        class _Home(BasePage):
            pass
        page = _Page()
        _Home(page).click("#login-btn")
        self.assertEqual(page.clicked, ["#login-btn"])


class TestComponentHealingScope(unittest.TestCase):
    """自愈开启时的作用域 —— 修复结果不得越出 root。"""

    def setUp(self):
        runtime.HEALED.clear()
        _Dialog.self_heal_enabled = True
        self.addCleanup(setattr, _Dialog, "self_heal_enabled", False)
        self.addCleanup(runtime.HEALED.clear)

    def _dialog(self, page):
        dlg = _Dialog(page)
        dlg.interceptor._store = runtime.FingerprintStore("")
        dlg.interceptor._store.put("_Dialog..btn-ok", FINGERPRINT)
        return dlg

    def test_interceptor_receives_root_as_scope(self):
        self.assertEqual(self._dialog(_Page()).interceptor.scope, ".modal")

    def test_snapshot_is_taken_inside_root(self):
        """快照必须带 root：采到整页就可能把组件的定位符修成页面别处的元素。"""
        page = _Page(broken=True)
        self._dialog(page).click(".btn-ok")
        self.assertEqual(page.snapshot_roots, [".modal"])

    def test_healed_selector_is_relative_and_rescoped(self):
        """自愈返回相对选择器，实际定位时重新拼上 root。"""
        page = _Page(broken=True)
        self._dialog(page).click(".btn-ok")
        self.assertEqual(len(runtime.HEALED), 1)
        self.assertEqual(runtime.HEALED[0]["new"], INSIDE,
                         "自愈结果应是组件内的相对选择器")
        self.assertEqual(page.clicked[-1], f".modal >> {INSIDE}",
                         "自愈后的选择器丢了作用域")

    def test_never_heals_to_element_outside_root(self):
        page = _Page(broken=True)
        self._dialog(page).click(".btn-ok")
        self.assertNotIn(OUTSIDE, [h["new"] for h in runtime.HEALED],
                         "自愈越出了 root，顶替到页面别处的无关元素")


if __name__ == "__main__":
    unittest.main()

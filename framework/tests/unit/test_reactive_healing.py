"""自愈时机回归测试 —— 守住「反应式拦截」这条线。

本文件存在的理由是一个真实缺陷：早期实现用 `locator.count() > 0` 在操作**之前**
探测选择器是否还有效。但 count() 不做自动等待 —— SPA 页面尚在渲染时目标元素还没
挂载，预探测会把「还没到」误判成「定位失效」，于是在半渲染的页面上启动自愈，
顶替到一个恰好已渲染的无关元素。用例照绿，点的却是别的按钮。

那正是整套机制唯一不能失守的地方：**绝不把真失败变成假通过**。
若本文件变红，说明自愈又回到了预探测语义，必须停用机制并修回。

运行：python3 -m unittest discover -s framework/tests/unit -t framework
"""
import sys
import types
import unittest

# core.base.base_page 需要 playwright 的类型符号；本测试不真正驱动浏览器，
# 缺失时补一个最小替身，使判定逻辑可脱离浏览器验证。
try:  # pragma: no cover
    import playwright.sync_api  # noqa: F401
except ImportError:  # pragma: no cover
    _stub = types.ModuleType("playwright.sync_api")
    _stub.Page = object
    _stub.Locator = object
    sys.modules.setdefault("playwright", types.ModuleType("playwright"))
    sys.modules.setdefault("playwright.sync_api", _stub)

from core.base.base_page import BasePage          # noqa: E402
from core.healing import runtime                  # noqa: E402

FINGERPRINT = {"tag": "button", "role": "button", "name": "登录"}
OTHER = '[data-testid="other"]'
# 页面上确实存在、且与指纹吻合的另一个按钮 —— 过早自愈就会顶替到它
SNAPSHOT = [{"tag": "button", "attrs": {"data-testid": "other"}, "role": "button",
             "name": "登录", "text": "登录", "classes": []}]


class _Locator:
    def __init__(self, selector, present, mode):
        self.selector, self._present, self._mode = selector, present, mode
        self.first = self

    def count(self):
        return 1 if self._present else 0

    def is_visible(self):
        return self._present

    def evaluate(self, js):
        return dict(FINGERPRINT, text="登录", classes=[])

    def click(self, **kwargs):
        if self._mode == "gone" and self.selector == "#login-btn":
            raise RuntimeError("Timeout 15000ms exceeded. waiting for locator('#login-btn')")
        if self._mode == "assertion":
            raise AssertionError("expected 3 got 4")
        return self.selector      # late 模式：Playwright 自动等待后成功


class _Page:
    """mode: late=元素稍后才渲染 / gone=元素真的没了 / assertion=断言失败"""

    url = "http://t/"

    def __init__(self, mode):
        self.mode = mode
        self.evaluated = 0

    def locator(self, selector):
        return _Locator(selector, present=(selector == OTHER), mode=self.mode)

    def evaluate(self, js, arg=None):
        self.evaluated += 1
        return SNAPSHOT if "querySelectorAll" in js else FINGERPRINT


class _DemoPage(BasePage):
    LOGIN_BTN = "#login-btn"      # P0: 登录按钮


class TestReactiveHealing(unittest.TestCase):
    def setUp(self):
        runtime.HEALED.clear()
        _DemoPage.self_heal_enabled = True
        self.addCleanup(setattr, _DemoPage, "self_heal_enabled", False)

    def _page_object(self, mode, tmpname):
        po = _DemoPage(_Page(mode))
        po.interceptor._store = runtime.FingerprintStore("")
        po.interceptor._store.put("_DemoPage.#login-btn", FINGERPRINT)
        return po

    def test_not_yet_rendered_does_not_heal(self):
        """元素只是还没渲染 —— Playwright 会等到它，绝不能自愈。

        这是本文件守的那个缺陷：预探测语义下此处会顶替到 OTHER。
        """
        po = self._page_object("late", "late")
        po.click("#login-btn")
        self.assertEqual(runtime.HEALED, [],
                         "元素尚未渲染时触发了自愈 —— 已退回预探测语义，"
                         "会在半渲染页面上顶替到无关元素")

    def test_genuine_location_failure_heals(self):
        """元素真的没了 —— 操作抛出定位失败后才自愈。"""
        po = self._page_object("gone", "gone")
        po.click("#login-btn")
        self.assertEqual(len(runtime.HEALED), 1)
        self.assertEqual(runtime.HEALED[0]["new"], OTHER)

    def test_assertion_failure_passes_through(self):
        """断言失败不是定位失败 —— 原样抛出，自愈绝不介入。

        介入断言失败等于替业务掩盖真实缺陷。
        """
        po = self._page_object("assertion", "assertion")
        with self.assertRaises(AssertionError):
            po.click("#login-btn")
        self.assertEqual(runtime.HEALED, [])

    def test_disabled_mode_never_touches_interceptor(self):
        """自愈关闭时行为与直接 locator() 逐字等价。"""
        _DemoPage.self_heal_enabled = False
        page = _Page("late")
        _DemoPage(page).click("#login-btn")
        self.assertEqual(page.evaluated, 0)
        self.assertEqual(runtime.HEALED, [])

    def test_healed_selector_reused_without_healing_again(self):
        """同一选择器第二次使用直接走缓存，不再重复推断。

        断言自愈发生的次数，而不是 evaluate 总次数 —— 后者还包含指纹采集，
        两者混在一起会让这条守卫测不准它声称的东西。
        """
        po = self._page_object("gone", "reuse")
        po.click("#login-btn")
        po.click("#login-btn")
        self.assertEqual(len(runtime.HEALED), 1)


if __name__ == "__main__":
    unittest.main()

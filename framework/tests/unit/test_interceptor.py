"""定位拦截器单测 —— 用假 page 对象，不需要浏览器。

运行：python3 -m unittest discover -s tests/unit -t .
"""
import os
import tempfile
import unittest

from core.exceptions import ElementLocationError, HealingError, VelocitaiError
from core.healing import runtime
from core.healing.interceptor import LocatorInterceptor, is_location_failure


class FakeLoc:
    def __init__(self, n, visible=True):
        self._n, self._v = n, visible
        self.first = self

    def count(self):
        return self._n

    def is_visible(self):
        return self._v

    def evaluate(self, js):
        return {"tag": "button", "role": "button", "name": "登录",
                "text": "登录", "classes": ["btn"]}


class FakePage:
    def __init__(self, hits=None, elements=None):
        self.hits = hits or {}
        self.elements = elements or []
        self.url = "http://t/"
        self.evaluated = 0

    def locator(self, sel):
        return FakeLoc(self.hits.get(sel, 0))

    def evaluate(self, js, arg=None):
        self.evaluated += 1
        if "querySelectorAll" in js:
            return self.elements
        return {"tag": "button", "role": "button", "name": "登录"}


class OwnerPage:
    LOGIN_BTN = "#login-btn"     # P0: 登录按钮


class TestLocationFailureClassification(unittest.TestCase):
    """自愈只允许介入元素定位失败。断言失败被误判为定位失败，
    就意味着自愈会去替业务掩盖真实缺陷。"""

    def test_own_exception_is_location_failure(self):
        self.assertTrue(is_location_failure(ElementLocationError("#x", "P", "C")))

    def test_timeout_is_location_failure(self):
        TE = type("TimeoutError", (Exception,), {})
        self.assertTrue(is_location_failure(TE("waiting for locator")))

    def test_strict_mode_violation_is_location_failure(self):
        self.assertTrue(is_location_failure(Exception("Error: strict mode violation: 2 elements")))

    def test_assertion_error_is_not_location_failure(self):
        self.assertFalse(is_location_failure(AssertionError("expected 3 got 4")))

    def test_value_error_is_not_location_failure(self):
        self.assertFalse(is_location_failure(ValueError("bad env")))

    def test_handle_failure_ignores_non_location_errors(self):
        itc = LocatorInterceptor(FakePage(), OwnerPage)
        self.assertIsNone(itc.handle_failure(AssertionError("nope"), "#x"))


class TestExceptionHierarchy(unittest.TestCase):
    def test_all_inherit_framework_base(self):
        # 调用方应当能一次性捕获本框架抛出的所有异常
        self.assertTrue(issubclass(ElementLocationError, VelocitaiError))
        self.assertTrue(issubclass(HealingError, VelocitaiError))

    def test_message_names_the_location(self):
        e = ElementLocationError("#login", "LoginPage", "LOGIN_BTN")
        self.assertIn("#login", str(e))
        self.assertIn("LoginPage.LOGIN_BTN", str(e))


class TestCurrent(unittest.TestCase):
    """current() 只查缓存，不碰页面。

    曾经这里是 resolve()，用 locator.count() > 0 做前置探测 —— 那是错的：
    count() 不做自动等待，SPA 页面尚在渲染时会把「还没挂载」误判成
    「定位失效」，于是在半渲染的页面上启动自愈，极易顶替到一个恰好已渲染
    的无关元素。见 TestReactiveHealing。
    """

    def setUp(self):
        runtime.HEALED.clear()
        runtime.PATCHED.clear()

    def test_returns_original_when_never_healed(self):
        page = FakePage()
        itc = LocatorInterceptor(page, OwnerPage)
        self.assertEqual(itc.current("#login-btn"), "#login-btn")
        self.assertEqual(page.evaluated, 0)      # 没碰页面

    def test_returns_healed_when_cached(self):
        itc = LocatorInterceptor(FakePage(), OwnerPage)
        itc._healed["#old"] = "#new"
        self.assertEqual(itc.current("#old"), "#new")


class TestHealBudget(unittest.TestCase):
    """愈不了的不反复重试，且总次数有上限。

    is_page_loaded() 这类轮询会对同一个选择器反复调用；若每次都抓一遍全页
    快照，代价极高而结论不变。
    """

    def setUp(self):
        runtime.HEALED.clear()

    def test_failed_selector_not_retried(self):
        page = FakePage(hits={}, elements=[])
        itc = LocatorInterceptor(page, OwnerPage)
        self.assertIsNone(itc.heal("#gone"))
        first = page.evaluated
        self.assertIsNone(itc.heal("#gone"))
        self.assertEqual(page.evaluated, first)   # 没有再抓一次快照

    def test_attempt_cap_enforced(self):
        page = FakePage(hits={}, elements=[])
        itc = LocatorInterceptor(page, OwnerPage)
        itc._attempts = itc.MAX_ATTEMPTS
        self.assertIsNone(itc.heal("#anything"))
        self.assertEqual(page.evaluated, 0)       # 达到上限后直接放弃


class TestWriteBackDisabledByDefault(unittest.TestCase):
    def test_patch_flag_defaults_false(self):
        itc = LocatorInterceptor(FakePage(), OwnerPage)
        self.assertFalse(itc.patch)
        self.assertFalse(itc.use_llm)


if __name__ == "__main__":
    unittest.main()
